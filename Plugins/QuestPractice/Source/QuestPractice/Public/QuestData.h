#pragma once
#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "Engine/DataAsset.h"
#include "QuestData.generated.h"
class UStaticMesh;
class USoundBase;

/** One editable weapon definition. Damage is positive; the ability applies it as a negative Health modifier. */
USTRUCT(BlueprintType)
struct QUESTPRACTICE_API FQuestWeaponRow : public FTableRowBase
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Weapon") FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Weapon", meta=(ClampMin="0.01")) float Damage=25.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Weapon", meta=(ClampMin="0.01")) float ShotInterval=.35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Weapon", meta=(ClampMin="1")) float Range=6000.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TSoftObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") TSoftObjectPtr<USoundBase> Sound;
    bool IsUsable() const;
};

/** Shared round settings; applying a definition is allowed only before a round or after its terminal result. */
UCLASS(BlueprintType)
class QUESTPRACTICE_API UQuestRoundDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Objective", meta=(ClampMin="1")) int32 RequiredKills=3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Objective", meta=(ClampMin="0")) float TimeLimit=90.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Spawning", meta=(ClampMin="1")) int32 MaxAlive=2;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Spawning", meta=(ClampMin="0.1")) float SpawnInterval=2.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Health", meta=(ClampMin="1")) float PlayerHealth=100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Health", meta=(ClampMin="1")) float BotHealth=50.f;
    bool IsUsable() const;
};
