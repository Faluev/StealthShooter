#include "QuestData.h"
bool FQuestWeaponRow::IsUsable() const
{
    return FMath::IsFinite(Damage) && Damage>0 && FMath::IsFinite(ShotInterval) && ShotInterval>0 && FMath::IsFinite(Range) && Range>0;
}
bool UQuestRoundDefinition::IsUsable() const
{
    return RequiredKills>0 && MaxAlive>0 && FMath::IsFinite(TimeLimit) && TimeLimit>=0 &&
        FMath::IsFinite(SpawnInterval) && SpawnInterval>=.1f && FMath::IsFinite(PlayerHealth) && PlayerHealth>=1 &&
        FMath::IsFinite(BotHealth) && BotHealth>=1;
}
