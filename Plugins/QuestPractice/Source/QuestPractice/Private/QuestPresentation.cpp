#include "QuestPresentation.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSequence.h"
#include "AssetRegistry/AssetRegistryModule.h"

UBlendSpace* UQuestPresentation::BuildRifleLocomotion(const FString& PackagePath,const TArray<UAnimSequence*>& Animations,const TArray<FVector>& Coordinates)
{
#if WITH_EDITOR
    if (Animations.IsEmpty() || Animations.Num()!=Coordinates.Num() || !Animations[0]) return nullptr;
    if (LoadObject<UBlendSpace>(nullptr,*PackagePath)) return nullptr; // Never replace an existing authored asset.
    auto* Package=CreatePackage(*PackagePath);
    auto* Blend=NewObject<UBlendSpace>(Package,*FPackageName::GetLongPackageAssetName(PackagePath),RF_Public|RF_Standalone);
    Blend->SetSkeleton(Animations[0]->GetSkeleton());
    for (int32 Axis=0;Axis<2;++Axis)
    {
        auto& Parameter=const_cast<FBlendParameter&>(Blend->GetBlendParameter(Axis));
        Parameter.DisplayName=Axis==0 ? TEXT("Forward speed") : TEXT("Right speed");
        Parameter.Min=-450.f; Parameter.Max=450.f; Parameter.GridNum=6; Parameter.bSnapToGrid=false;
    }
    for (int32 Index=0;Index<Animations.Num();++Index)
        if (Animations[Index]) Blend->AddSample(Animations[Index],Coordinates[Index]);
    Blend->ValidateSampleData(); Blend->ResampleData(); Blend->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Blend);
    return Blend;
#else
    return nullptr;
#endif
}
