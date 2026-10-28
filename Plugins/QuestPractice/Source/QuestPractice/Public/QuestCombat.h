#pragma once
#include "CoreMinimal.h"
#include "CombatPractice.h"
#include "QuestCombat.generated.h"

class AQuestDirector;
class AQuestBot;
class UBoxComponent;
class UTextRenderComponent;
class UCombatAttributeSet;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FQuestBotDied, AQuestBot*, Victim, AActor*, Killer);

/** Extends the completed combat player only on the new map. */
UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestPlayer : public ACombatPlayer
{
    GENERATED_BODY()
public:
    AQuestPlayer();
    virtual void BeginPlay() override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    UFUNCTION(BlueprintCallable, Category="Combat") bool TryFire();
    UFUNCTION(BlueprintCallable, Category="Quest") void RestartQuestRun();
    UFUNCTION(BlueprintPure, Category="Combat") FVector GetShotStart() const;
    UFUNCTION(BlueprintPure, Category="Combat") bool TraceAim(FHitResult& Hit) const;
    UFUNCTION(BlueprintPure, Category="Quest") AQuestDirector* GetQuestDirector() const;
    void PresentShot(const FVector& End);
    UPROPERTY(EditDefaultsOnly, Category="Combat") TSubclassOf<UGameplayAbility> FireAbility;
    UPROPERTY(EditDefaultsOnly, Category="Combat") TSubclassOf<UGameplayEffect> ShotDamageEffect;
    UPROPERTY(EditDefaultsOnly, Category="Combat") TSubclassOf<UGameplayCueNotify_Static> ShotCueClass;
    UPROPERTY(EditDefaultsOnly, Category="Presentation") TObjectPtr<USoundBase> ShotSound;
    UPROPERTY(EditDefaultsOnly, Category="Presentation") TObjectPtr<UMaterialInterface> TracerMaterial;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weapon") TObjectPtr<UStaticMeshComponent> Rifle;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 ShotsFired = 0;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 Hits = 0;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 ShotCues = 0;
private:
    void FirePressed();
    void OnPlayerHealthChanged(const FOnAttributeChangeData& Change);
    bool bDeathReported = false;
};

/** Adds GAS Health/death to the previous bot without altering that earlier practical. */
UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestBot : public ACombatBot
{
    GENERATED_BODY()
public:
    AQuestBot();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintPure, Category="Health") float GetBotHealth() const;
    UFUNCTION(BlueprintPure, Category="Health") bool IsDead() const { return bDead; }
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Attributes") TObjectPtr<UCombatAttributeSet> BotAttributes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Health") TObjectPtr<UTextRenderComponent> HealthLabel;
    UPROPERTY(BlueprintReadOnly, Category="Health") bool bDead = false;
    UPROPERTY(BlueprintAssignable, Category="Health") FQuestBotDied OnDied;
private:
    void OnHealthChanged(const FOnAttributeChangeData& Change);
};

/** Capacity counts living bots, not corpses. Destruction is not equivalent to a credited kill. */
UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestBotSpawner : public AActor
{
    GENERATED_BODY()
public:
    AQuestBotSpawner();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, Category="Spawning") void SetSpawning(bool bEnabled);
    UFUNCTION(BlueprintCallable, Category="Spawning") AQuestBot* TrySpawnBot();
    UFUNCTION(BlueprintPure, Category="Spawning") int32 GetLivingCount() const;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Spawning") TObjectPtr<UBoxComponent> SpawnArea;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spawning") TSubclassOf<AQuestBot> BotClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spawning", meta=(ClampMin="1")) int32 MaxAlive = 2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spawning", meta=(ClampMin="0.1")) float SpawnInterval = 2.f;
    UPROPERTY(BlueprintReadOnly, Category="Spawning") bool bSpawning = false;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 TotalSpawned = 0;
private:
    UFUNCTION() void HandleBotDied(AQuestBot* Victim, AActor* Killer);
    TArray<TWeakObjectPtr<AQuestBot>> LivingBots;
    FTimerHandle SpawnTimer;
};

UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    UFUNCTION(BlueprintCallable, Category="Quest") void RestartRun();
    UFUNCTION(BlueprintPure, Category="Quest") AQuestDirector* GetDirector() const { return Director; }
    UPROPERTY(BlueprintReadOnly, Category="Quest") TObjectPtr<AQuestDirector> Director;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 RestartCount = 0;
private:
    UFUNCTION() void OnRunEnded(bool bSuccess, FText Reason);
};

UCLASS(Blueprintable)
class QUESTPRACTICE_API UQuestShootAbility : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UQuestShootAbility();
    virtual bool CanActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* SourceTags=nullptr, const FGameplayTagContainer* TargetTags=nullptr,
        FGameplayTagContainer* RelevantTags=nullptr) const override;
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        const FGameplayAbilityActivationInfo Activation, const FGameplayEventData* EventData) override;
};
UCLASS(Blueprintable)
class QUESTPRACTICE_API UQuestDamageEffect : public UGameplayEffect
{
    GENERATED_BODY()
public: UQuestDamageEffect();
};
UCLASS(Blueprintable)
class QUESTPRACTICE_API UQuestShotCooldown : public UGameplayEffect
{
    GENERATED_BODY()
public: UQuestShotCooldown();
};
UCLASS(Blueprintable)
class QUESTPRACTICE_API UQuestShotCue : public UGameplayCueNotify_Static
{
    GENERATED_BODY()
public:
    UQuestShotCue();
    virtual bool OnExecute_Implementation(AActor* TargetActor,const FGameplayCueParameters& Parameters) const override;
};
