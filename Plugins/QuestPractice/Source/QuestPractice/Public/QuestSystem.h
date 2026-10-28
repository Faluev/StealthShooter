#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "QuestSystem.generated.h"

class AQuestBot;
class AQuestObjective;

UENUM(BlueprintType)
enum class EQuestState : uint8 { Inactive, Active, Completed, Failed };

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FQuestChanged, AQuestObjective*, Quest);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FQuestListChanged);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FQuestRunEnded, bool, bSuccess, FText, Reason);

/** Base contract: idempotent terminal states and a common failure path for every objective type. */
UCLASS(Abstract, Blueprintable)
class QUESTPRACTICE_API AQuestObjective : public AActor
{
    GENERATED_BODY()
public:
    AQuestObjective();
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable, Category="Quest") virtual void StartQuest();
    UFUNCTION(BlueprintCallable, Category="Quest") virtual void ResetQuest();
    UFUNCTION(BlueprintCallable, Category="Quest") void FailQuest(FText Reason);
    UFUNCTION(BlueprintPure, Category="Quest") float GetRemainingSeconds() const;
    UFUNCTION(BlueprintPure, Category="Quest") virtual FText GetProgressText() const;
    virtual void NotifyBotKilled(AQuestBot* Victim, AActor* Killer) {}

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quest") int32 Order = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quest") FText Title;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quest", meta=(ClampMin="0")) float TimeLimit = 90.f;
    UPROPERTY(BlueprintReadOnly, Category="Quest") EQuestState State = EQuestState::Inactive;
    UPROPERTY(BlueprintReadOnly, Category="Quest") FText FailureReason;
    UPROPERTY(BlueprintAssignable, Category="Quest") FQuestChanged OnChanged;
protected:
    void CompleteQuest();
    float Deadline = 0.f;
};

/** Owns its counter and kill filtering; the manager never knows how this objective measures progress. */
UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestKillBots : public AQuestObjective
{
    GENERATED_BODY()
public:
    AQuestKillBots();
    virtual void StartQuest() override;
    virtual void ResetQuest() override;
    virtual void NotifyBotKilled(AQuestBot* Victim, AActor* Killer) override;
    virtual FText GetProgressText() const override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quest", meta=(ClampMin="1")) int32 RequiredKills = 3;
    UPROPERTY(BlueprintReadOnly, Category="Quest") int32 CurrentKills = 0;
private:
    TSet<TWeakObjectPtr<AQuestBot>> CountedVictims;
};

/** Sequential orchestration with explicit subscriptions; objective subclasses remain independent. */
UCLASS(Blueprintable)
class QUESTPRACTICE_API AQuestDirector : public AActor
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Quest") void StartRun();
    UFUNCTION(BlueprintCallable, Category="Quest") void FailActiveQuest(FText Reason);
    UFUNCTION(BlueprintCallable, Category="Quest") void NotifyBotKilled(AQuestBot* Victim, AActor* Killer);
    UFUNCTION(BlueprintPure, Category="Quest") AQuestObjective* GetActiveQuest() const;
    UFUNCTION(BlueprintPure, Category="Quest") bool IsRunActive() const;
    UPROPERTY(BlueprintReadOnly, Category="Quest") TArray<TObjectPtr<AQuestObjective>> Quests;
    UPROPERTY(BlueprintReadOnly, Category="Quest") int32 ActiveIndex = 0;
    UPROPERTY(BlueprintReadOnly, Category="Quest") bool bFinished = false;
    UPROPERTY(BlueprintReadOnly, Category="Quest") bool bSucceeded = false;
    UPROPERTY(BlueprintReadOnly, Category="Quest") FText ResultReason;
    UPROPERTY(BlueprintAssignable, Category="Quest") FQuestListChanged OnUpdated;
    UPROPERTY(BlueprintAssignable, Category="Quest") FQuestRunEnded OnRunEnded;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UFUNCTION() void HandleQuestChanged(AQuestObjective* Quest);
    void FinishRun(bool bSuccess, FText Reason);
};
