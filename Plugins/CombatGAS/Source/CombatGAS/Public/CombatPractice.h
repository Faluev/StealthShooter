#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "AbilitySystemInterface.h"
#include "Abilities/GameplayAbility.h"
#include "GameplayEffect.h"
#include "GameplayCueNotify_Static.h"
#include "Blueprint/UserWidget.h"
#include "CombatPractice.generated.h"

class UCombatAttributeSet;
class UProgressBar;
class UTextBlock;
class UStaticMeshComponent;
class USceneComponent;
class UCameraComponent;
class USpringArmComponent;
class USoundBase;
class UMaterialInterface;
struct FOnAttributeChangeData;

UENUM(BlueprintType)
enum class ECombatBotState : uint8 { Patrol, DrawingWeapon, Combat, Searching };

/** Shared native ASC ownership. Presentation and gameplay assets remain editable Blueprints. */
UCLASS(Blueprintable)
class COMBATGAS_API ACombatPlayer : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    ACombatPlayer();
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override { return AbilitySystem; }
    virtual void BeginPlay() override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    UFUNCTION(BlueprintPure, Category="Health") float GetHealth() const;
    UFUNCTION(BlueprintPure, Category="Health") float GetMaxHealth() const;
    UFUNCTION(BlueprintPure, Category="Health") bool IsAlive() const;
    UFUNCTION(BlueprintCallable, Category="Practice") void RestartPractice();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Abilities") TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Attributes") TObjectPtr<UCombatAttributeSet> Attributes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera") TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(EditDefaultsOnly, Category="Interface") TSubclassOf<UUserWidget> HUDClass;
    UPROPERTY(BlueprintReadOnly, Category="Interface") TObjectPtr<UUserWidget> HUD;
private:
    void MoveForward(float Value);
    void MoveRight(float Value);
    void HealthChanged(const FOnAttributeChangeData& Change);
};

/** Sight/patrol orchestration only. Shot execution, damage and cadence belong to GAS. */
UCLASS(Blueprintable)
class COMBATGAS_API ACombatBot : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    ACombatBot();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override { return AbilitySystem; }
    UFUNCTION(BlueprintPure, Category="Combat") bool CanShootTarget() const;
    UFUNCTION(BlueprintPure, Category="Combat") FVector GetMuzzleLocation() const;
    UFUNCTION(BlueprintPure, Category="Combat") float GetShotCooldownRemaining() const;
    UFUNCTION(BlueprintCallable, Category="Combat") void PresentShot(const FVector& End);
    UFUNCTION(BlueprintCallable, Category="Combat") bool RequestShot();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Abilities") TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weapon") TObjectPtr<USceneComponent> WeaponRoot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weapon") TObjectPtr<UStaticMeshComponent> WeaponBody;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weapon") TObjectPtr<UStaticMeshComponent> WeaponBarrel;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weapon") TObjectPtr<USceneComponent> Muzzle;
    UPROPERTY(EditDefaultsOnly, Category="Abilities") TSubclassOf<UGameplayAbility> ShootAbility;
    UPROPERTY(EditDefaultsOnly, Category="Abilities") TSubclassOf<UGameplayEffect> DamageEffect;
    UPROPERTY(EditDefaultsOnly, Category="Abilities") TSubclassOf<UGameplayCueNotify_Static> ShotCue;
    UPROPERTY(EditDefaultsOnly, Category="Presentation") TObjectPtr<USoundBase> ShotSound;
    UPROPERTY(EditDefaultsOnly, Category="Presentation") TObjectPtr<UMaterialInterface> TracerMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Patrol", meta=(MakeEditWidget=true)) TArray<FVector> PatrolPoints;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sight") float SightRadius = 1600.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sight") float PeripheralVisionDegrees = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sight") float ForgetDelay = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float DrawWeaponDuration = .65f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") TObjectPtr<ACombatPlayer> Target;
    UPROPERTY(BlueprintReadOnly, Category="Combat") ECombatBotState State = ECombatBotState::Patrol;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bWeaponDrawn = false;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 ShotCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 CueCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") int32 HitCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Diagnostics") TArray<float> ShotTimes;
private:
    bool HasLineOfSight() const;
    bool CanSeePlayer() const;
    void SetWeaponDrawn(bool bDrawn);
    void UpdatePatrol();
    float LostSightTime = 0.f;
    float DrawStartedAt = 0.f;
    int32 PatrolIndex = 0;
};

UCLASS(Blueprintable)
class COMBATGAS_API UCombatShootAbility : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UCombatShootAbility();
    virtual bool CanActivateAbility(const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags = nullptr,
        const FGameplayTagContainer* TargetTags = nullptr, FGameplayTagContainer* RelevantTags = nullptr) const override;
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo,
        const FGameplayEventData* TriggerEventData) override;
};

UCLASS(Blueprintable)
class COMBATGAS_API UCombatDamageEffect : public UGameplayEffect
{
    GENERATED_BODY()
public: UCombatDamageEffect();
};

UCLASS(Blueprintable)
class COMBATGAS_API UCombatShotCooldown : public UGameplayEffect
{
    GENERATED_BODY()
public: UCombatShotCooldown();
};

UCLASS(Blueprintable)
class COMBATGAS_API UCombatShotCue : public UGameplayCueNotify_Static
{
    GENERATED_BODY()
public:
    UCombatShotCue();
    virtual bool OnExecute_Implementation(AActor* MyTarget, const FGameplayCueParameters& Parameters) const override;
};

/** Event-driven health bar; Tick only displays bot state/cooldown for the demonstration. */
UCLASS(Blueprintable)
class COMBATGAS_API UCombatHUD : public UUserWidget
{
    GENERATED_BODY()
public:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaSeconds) override;
    UFUNCTION(BlueprintPure, Category="Health") float GetDisplayedHealthPercent() const;
private:
    void RefreshHealth(const FOnAttributeChangeData& Change);
    void UpdateHealth();
    UPROPERTY() TObjectPtr<UProgressBar> HealthBar;
    UPROPERTY() TObjectPtr<UTextBlock> HealthText;
    UPROPERTY() TObjectPtr<UTextBlock> BotText;
    TWeakObjectPtr<ACombatPlayer> Player;
    FDelegateHandle HealthHandle;
    FDelegateHandle MaxHealthHandle;
};

UCLASS(Blueprintable)
class COMBATGAS_API ACombatGameMode : public AGameModeBase
{
    GENERATED_BODY()
};

/** Short-lived cosmetic geometry, spawned exclusively by GC_BotShot. No collision or damage. */
UCLASS()
class COMBATGAS_API ACombatShotVisual : public AActor
{
    GENERATED_BODY()
public:
    ACombatShotVisual();
    void Initialize(const FVector& Start, const FVector& End, UMaterialInterface* Material);
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Tracer;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Flash;
};
