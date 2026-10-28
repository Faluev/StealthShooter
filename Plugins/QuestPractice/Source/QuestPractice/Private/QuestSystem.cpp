#include "QuestSystem.h"
#include "QuestCombat.h"
#include "EngineUtils.h"

AQuestObjective::AQuestObjective()
{
    PrimaryActorTick.bCanEverTick=true;
    Title=FText::FromString(TEXT("Задание"));
}
void AQuestObjective::StartQuest()
{
    if (State!=EQuestState::Inactive) return;
    State=EQuestState::Active;
    FailureReason=FText::GetEmpty();
    Deadline=GetWorld()->GetTimeSeconds()+FMath::Max(0.f,TimeLimit);
    OnChanged.Broadcast(this);
}
void AQuestObjective::ResetQuest()
{
    State=EQuestState::Inactive; Deadline=0.f; FailureReason=FText::GetEmpty();
}
float AQuestObjective::GetRemainingSeconds() const
{
    return State==EQuestState::Active && TimeLimit>0.f ? FMath::Max(0.f,Deadline-GetWorld()->GetTimeSeconds()) : 0.f;
}
void AQuestObjective::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (State==EQuestState::Active && TimeLimit>0.f && GetRemainingSeconds()<=0.f)
        FailQuest(FText::FromString(TEXT("Время вышло. Цель не достигнута.")));
}
void AQuestObjective::FailQuest(FText Reason)
{
    if (State!=EQuestState::Active) return;
    State=EQuestState::Failed; FailureReason=Reason; OnChanged.Broadcast(this);
}
void AQuestObjective::CompleteQuest()
{
    if (State!=EQuestState::Active) return;
    State=EQuestState::Completed; OnChanged.Broadcast(this);
}
FText AQuestObjective::GetProgressText() const { return Title; }

AQuestKillBots::AQuestKillBots() { Title=FText::FromString(TEXT("Уничтожить ботов")); }
void AQuestKillBots::StartQuest()
{
    if (State!=EQuestState::Inactive) return;
    RequiredKills=FMath::Max(1,RequiredKills);
    CurrentKills=0; CountedVictims.Empty(); Super::StartQuest();
}
void AQuestKillBots::ResetQuest()
{
    CurrentKills=0; CountedVictims.Empty(); Super::ResetQuest();
}
void AQuestKillBots::NotifyBotKilled(AQuestBot* Victim,AActor* Killer)
{
    if (State!=EQuestState::Active || !IsValid(Victim) || !Victim->IsDead() ||
        !IsValid(Killer) || !Killer->IsA<AQuestPlayer>() || CountedVictims.Contains(Victim)) return;
    CountedVictims.Add(Victim);
    CurrentKills=FMath::Min(CurrentKills+1,RequiredKills);
    if (CurrentKills>=RequiredKills) CompleteQuest();
    else OnChanged.Broadcast(this);
}
FText AQuestKillBots::GetProgressText() const
{
    return FText::FromString(FString::Printf(TEXT("Уничтожено ботов: %d / %d"),CurrentKills,RequiredKills));
}

void AQuestDirector::StartRun()
{
    for (const auto& Quest:Quests) if (IsValid(Quest.Get())) Quest->OnChanged.RemoveDynamic(this,&AQuestDirector::HandleQuestChanged);
    Quests.Empty(); ActiveIndex=0; bFinished=false; bSucceeded=false; ResultReason=FText::GetEmpty();
    for (TActorIterator<AQuestObjective> It(GetWorld());It;++It) Quests.Add(*It);
    Quests.Sort([](const AQuestObjective& A,const AQuestObjective& B){return A.Order<B.Order;});
    for (int32 Index=0;Index<Quests.Num();++Index)
    {
        if (Index>0 && Quests[Index]->Order==Quests[Index-1]->Order)
        {
            FinishRun(false,FText::FromString(TEXT("Ошибка настройки: номера заданий совпадают.")));return;
        }
        Quests[Index]->ResetQuest();
        Quests[Index]->OnChanged.AddUniqueDynamic(this,&AQuestDirector::HandleQuestChanged);
    }
    if (Quests.IsEmpty()) { FinishRun(false,FText::FromString(TEXT("На уровне не настроены задания.")));return; }
    Quests[0]->StartQuest();
    OnUpdated.Broadcast();
}
AQuestObjective* AQuestDirector::GetActiveQuest() const { return Quests.IsValidIndex(ActiveIndex) ? Quests[ActiveIndex].Get() : nullptr; }
bool AQuestDirector::IsRunActive() const { return !bFinished && GetActiveQuest() && GetActiveQuest()->State==EQuestState::Active; }
void AQuestDirector::FailActiveQuest(FText Reason)
{
    if (IsRunActive()) GetActiveQuest()->FailQuest(Reason);
}
void AQuestDirector::NotifyBotKilled(AQuestBot* Victim,AActor* Killer)
{
    if (IsRunActive()) GetActiveQuest()->NotifyBotKilled(Victim,Killer);
}
void AQuestDirector::HandleQuestChanged(AQuestObjective* Quest)
{
    OnUpdated.Broadcast();
    if (bFinished || Quest!=GetActiveQuest()) return;
    if (Quest->State==EQuestState::Failed) FinishRun(false,Quest->FailureReason);
    else if (Quest->State==EQuestState::Completed)
    {
        if (ActiveIndex+1<Quests.Num()) { ++ActiveIndex; Quests[ActiveIndex]->StartQuest(); }
        else FinishRun(true,FText::FromString(TEXT("Все задания выполнены. Площадка зачищена.")));
    }
}
void AQuestDirector::FinishRun(bool bSuccess,FText Reason)
{
    if (bFinished) return;
    bFinished=true; bSucceeded=bSuccess; ResultReason=Reason;
    OnUpdated.Broadcast(); OnRunEnded.Broadcast(bSuccess,Reason);
}
void AQuestDirector::EndPlay(const EEndPlayReason::Type Reason)
{
    for (const auto& Quest:Quests) if (IsValid(Quest.Get())) Quest->OnChanged.RemoveDynamic(this,&AQuestDirector::HandleQuestChanged);
    Super::EndPlay(Reason);
}
