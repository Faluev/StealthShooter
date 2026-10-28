#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "QuestPresentation.generated.h"
class UBlendSpace;
class UAnimSequence;
/** Editor recipe helper; runtime uses the saved, cooked BlendSpace asset. */
UCLASS()
class QUESTPRACTICE_API UQuestPresentation : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Quest|Presentation")
    static UBlendSpace* BuildRifleLocomotion(const FString& PackagePath,const TArray<UAnimSequence*>& Animations,const TArray<FVector>& Coordinates);
};
