#if WITH_DEV_AUTOMATION_TESTS

#include "QuestCombat.h"
#include "QuestSystem.h"
#include "Engine/World.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FQuestDeadlineTest, "QuestPractice.KillDeadline",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FQuestDeadlineTest::RunTest(const FString& Parameters)
{
    FTestWorldWrapper TestWorld;
    if (!TestTrue(TEXT("Created test world"), TestWorld.CreateTestWorld(EWorldType::Game)))
        return false;
    UWorld* World = TestWorld.GetTestWorld();

    AQuestKillBots* Quest = World->SpawnActor<AQuestKillBots>();
    AQuestPlayer* Player = World->SpawnActor<AQuestPlayer>(
        FVector(400, 0, 0), FRotator::ZeroRotator);
    AQuestBot* Bot = World->SpawnActor<AQuestBot>(
        FVector(-400, 0, 0), FRotator::ZeroRotator);
    if (!TestNotNull(TEXT("Quest"), Quest) ||
        !TestNotNull(TEXT("Player"), Player) ||
        !TestNotNull(TEXT("Bot"), Bot))
        return false;

    Quest->RequiredKills = 1;
    Bot->bDead = true;

    auto StartAndAdvanceClock = [&](float TimeLimit, float Elapsed)
    {
        Quest->ResetQuest();
        Quest->TimeLimit = TimeLimit;
        Quest->StartQuest();
        // Advance world time without running the quest's deadline tick.
        World->Tick(LEVELTICK_TimeOnly, Elapsed);
        TestTrue(TEXT("Quest still awaits its first actor tick"),
            Quest->State == EQuestState::Active);
        Quest->NotifyBotKilled(Bot, Player);
    };

    constexpr float TimeLimit = 0.125f;
    StartAndAdvanceClock(TimeLimit, TimeLimit / 2);
    TestTrue(TEXT("A kill before expiry completes the quest"), Quest->State == EQuestState::Completed);
    TestEqual(TEXT("The timely kill counts"), Quest->CurrentKills, 1);

    StartAndAdvanceClock(TimeLimit, TimeLimit);
    TestTrue(TEXT("A kill at expiry fails the quest"), Quest->State == EQuestState::Failed);
    TestEqual(TEXT("A kill at expiry does not count"), Quest->CurrentKills, 0);

    StartAndAdvanceClock(TimeLimit, TimeLimit * 2);
    TestTrue(TEXT("A kill past expiry fails the quest"), Quest->State == EQuestState::Failed);
    TestEqual(TEXT("A late kill does not count"), Quest->CurrentKills, 0);

    StartAndAdvanceClock(0.0f, TimeLimit * 2);
    TestTrue(TEXT("Untimed quests still complete"), Quest->State == EQuestState::Completed);
    return true;
}

#endif
