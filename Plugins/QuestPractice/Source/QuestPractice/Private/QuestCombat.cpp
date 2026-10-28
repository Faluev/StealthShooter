#include "QuestCombat.h"
#include "QuestSystem.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSequence.h"
#include "CombatAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystemGlobals.h"
#include "GameplayCueManager.h"
#include "GameplayCueSet.h"
#include "GameplayEffectExtension.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
#include "NativeGameplayTags.h"
#include "AIController.h"
#include "NavigationSystem.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/InputComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/TextRenderComponent.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_QuestShotCue,"GameplayCue.Quest.Shot");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_QuestShotCooldown,"Cooldown.Player.QuestShot");

AQuestPlayer::AQuestPlayer()
{
    Rifle=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Rifle"));
    Rifle->SetupAttachment(GetMesh(),TEXT("hand_r"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Rifle->SetStaticMesh(Shape.Object);
    Rifle->SetRelativeLocation(FVector::ZeroVector);
    Rifle->SetRelativeRotation(FRotator(18,82,9));
    Rifle->SetRelativeScale3D(FVector(1,1,1));
    Rifle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Rifle->SetGenerateOverlapEvents(false);
    CameraBoom->TargetArmLength=350.f;
    CameraBoom->SocketOffset=FVector(0,55,65);
    bUseControllerRotationYaw=true;
    GetCharacterMovement()->bOrientRotationToMovement=false;
}
void AQuestPlayer::BeginPlay()
{
    Super::BeginPlay();
    if (ArmedLocomotion) { GetMesh()->PlayAnimation(ArmedLocomotion,true); }
    AbilitySystem->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).AddUObject(this,&AQuestPlayer::OnPlayerHealthChanged);
    if (HasAuthority() && FireAbility) AbilitySystem->GiveAbility(FGameplayAbilitySpec(FireAbility,1));
    if (ShotCueClass)
        UAbilitySystemGlobals::Get().GetGameplayCueManager()->GetRuntimeCueSet()->AddCues({FGameplayCueReferencePair(TAG_QuestShotCue,FSoftObjectPath(ShotCueClass.Get()))});
}
// Full-body Epic rifle poses blend by local velocity, keeping both hands on the weapon.
// Acceleration and braking feed continuous velocity instead of hard pose changes.
static void UpdateRiflePose(ACharacter* Character,UBlendSpace* Locomotion,UAnimSequence* Fall,float DeltaSeconds)
{
    if (auto* Instance=Character->GetMesh()->GetSingleNodeInstance())
    {
        UAnimationAsset* Desired=Character->GetCharacterMovement()->IsFalling() && Fall ? static_cast<UAnimationAsset*>(Fall) : static_cast<UAnimationAsset*>(Locomotion);
        if (Instance->CurrentAsset!=Desired) Instance->SetAnimationAsset(Desired,true,1.f);
        const FVector Velocity=Character->GetActorRotation().UnrotateVector(Character->GetVelocity());
        const FVector Position(Velocity.X,Velocity.Y,0);
        Instance->SetBlendSpacePosition(Position);
    }
}
void AQuestPlayer::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (ArmedLocomotion) UpdateRiflePose(this,ArmedLocomotion,ArmedFall,DeltaSeconds);
}
void AQuestPlayer::EndPlay(const EEndPlayReason::Type Reason)
{
    if (HUD) HUD->RemoveFromParent();
    Super::EndPlay(Reason);
}
void AQuestPlayer::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    if (HasActorBegunPlay() && !HUD && HUDClass)
    {
        if (auto* PC=Cast<APlayerController>(NewController))
        {
            HUD=CreateWidget<UUserWidget>(PC,HUDClass);
            if (HUD) HUD->AddToViewport();
        }
    }
}
void AQuestPlayer::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->KeyBindings.RemoveAll([](const FInputKeyBinding& Binding){return Binding.Chord.Key==EKeys::R;});
    Input->BindKey(EKeys::LeftMouseButton,IE_Pressed,this,&AQuestPlayer::FirePressed);
    Input->BindKey(EKeys::R,IE_Pressed,this,&AQuestPlayer::RestartQuestRun);
}
void AQuestPlayer::FirePressed() { TryFire(); }
bool AQuestPlayer::TryFire() { return FireAbility && AbilitySystem->TryActivateAbilityByClass(FireAbility); }
AQuestDirector* AQuestPlayer::GetQuestDirector() const
{
    const auto* Mode=Cast<AQuestGameMode>(GetWorld()->GetAuthGameMode());
    return Mode ? Mode->GetDirector() : nullptr;
}
void AQuestPlayer::RestartQuestRun()
{
    if (auto* Mode=Cast<AQuestGameMode>(GetWorld()->GetAuthGameMode())) Mode->RestartRun();
}
FVector AQuestPlayer::GetShotStart() const { return Rifle->GetSocketLocation(TEXT("Muzzle")); }
bool AQuestPlayer::TraceAim(FHitResult& Hit) const
{
    const FVector Start=FollowCamera->GetComponentLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(QuestAim),false,this);
    return GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+FollowCamera->GetForwardVector()*6000.f,ECC_Visibility,Query);
}
void AQuestPlayer::OnPlayerHealthChanged(const FOnAttributeChangeData& Change)
{
    if (Change.NewValue<=0.f && !bDeathReported)
    {
        bDeathReported=true;
        if (auto* Director=GetQuestDirector()) Director->FailActiveQuest(FText::FromString(TEXT("Игрок погиб. Попробуйте ещё раз.")));
    }
}
void AQuestPlayer::PresentShot(const FVector& End)
{
    ++ShotCues;
    if (auto* Visual=GetWorld()->SpawnActor<ACombatShotVisual>()) Visual->Initialize(GetShotStart(),End,TracerMaterial);
    if (ShotSound) UGameplayStatics::PlaySoundAtLocation(this,ShotSound,GetShotStart(),.45f);
}

AQuestBot::AQuestBot()
{
    BotAttributes=CreateDefaultSubobject<UCombatAttributeSet>(TEXT("BotAttributes"));
    BotAttributes->InitMaxHealth(50.f); BotAttributes->InitHealth(50.f);
    HealthLabel=CreateDefaultSubobject<UTextRenderComponent>(TEXT("HealthLabel"));
    HealthLabel->SetupAttachment(RootComponent);
    HealthLabel->SetRelativeLocation(FVector(0,0,120));
    HealthLabel->SetHorizontalAlignment(EHTA_Center);
    HealthLabel->SetWorldSize(19.f);
    HealthLabel->SetTextRenderColor(FColor(255,180,110));
}
void AQuestBot::BeginPlay()
{
    AbilitySystem->AddAttributeSetSubobject(BotAttributes.Get());
    Super::BeginPlay();
    AbilitySystem->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).AddUObject(this,&AQuestBot::OnHealthChanged);
    HealthLabel->SetText(FText::AsNumber(FMath::RoundToInt(GetBotHealth())));
    if (ArmedLocomotion) GetMesh()->PlayAnimation(ArmedLocomotion,true);
    WeaponBarrel->SetVisibility(false);
    GetCharacterMovement()->RotationRate=FRotator(0,240,0);
    GetCharacterMovement()->MaxAcceleration=650.f;
    GetCharacterMovement()->BrakingDecelerationWalking=650.f;
    GetCharacterMovement()->bUseRVOAvoidance=true;
    GetCharacterMovement()->AvoidanceConsiderationRadius=240.f;
}
float AQuestBot::GetBotHealth() const { return BotAttributes->GetHealth(); }
void AQuestBot::Tick(float DeltaSeconds)
{
    if (bDead) return;
    const auto* Mode=Cast<AQuestGameMode>(GetWorld()->GetAuthGameMode());
    if (Mode && Mode->GetDirector() && !Mode->GetDirector()->IsRunActive()) return;
    Super::Tick(DeltaSeconds);
    // The inherited combat logic controls sight, damage and cooldown. Presentation
    // follows the hand socket instead of rotating a floating gun independently.
    WeaponRoot->AttachToComponent(GetMesh(),FAttachmentTransformRules::SnapToTargetNotIncludingScale,TEXT("hand_r"));
    WeaponRoot->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator::ZeroRotator);
    WeaponBody->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(18,82,9));
    WeaponBody->SetRelativeScale3D(FVector::OneVector);
    Muzzle->SetWorldLocation(WeaponBody->GetSocketLocation(TEXT("Muzzle")));
    if (ArmedLocomotion) UpdateRiflePose(this,ArmedLocomotion,ArmedFall,DeltaSeconds);
    const auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if (Camera) HealthLabel->SetWorldRotation((Camera->GetCameraLocation()-HealthLabel->GetComponentLocation()).Rotation());
}
void AQuestBot::OnHealthChanged(const FOnAttributeChangeData& Change)
{
    HealthLabel->SetText(FText::AsNumber(FMath::RoundToInt(GetBotHealth())));
    if (Change.NewValue>0.f || bDead) return;
    bDead=true;
    State=ECombatBotState::Patrol; bWeaponDrawn=false;
    AActor* Killer=Change.GEModData ? Change.GEModData->EffectSpec.GetContext().GetOriginalInstigator() : nullptr;
    AbilitySystem->CancelAllAbilities();
    SetActorTickEnabled(false);
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    if (auto* AI=Cast<AAIController>(GetController())) { AI->StopMovement(); AI->UnPossess(); AI->Destroy(); }
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HealthLabel->SetVisibility(false);
    WeaponRoot->SetVisibility(false,true);
    GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
    GetMesh()->SetSimulatePhysics(true);
    OnDied.Broadcast(this,Killer);
    SetLifeSpan(4.f);
}

AQuestBotSpawner::AQuestBotSpawner()
{
    SpawnArea=CreateDefaultSubobject<UBoxComponent>(TEXT("SpawnArea"));
    RootComponent=SpawnArea; SpawnArea->SetBoxExtent(FVector(300,450,100));
    SpawnArea->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AQuestBotSpawner::SetSpawning(bool bEnabled)
{
    bSpawning=bEnabled;
    GetWorldTimerManager().ClearTimer(SpawnTimer);
    if (bEnabled)
    {
        TrySpawnBot();
        GetWorldTimerManager().SetTimer(SpawnTimer,FTimerDelegate::CreateWeakLambda(this,[this](){TrySpawnBot();}),FMath::Max(.1f,SpawnInterval),true);
    }
}
int32 AQuestBotSpawner::GetLivingCount() const
{
    int32 Count=0; for (const auto& Bot:LivingBots) if (Bot.IsValid() && !Bot->IsDead()) ++Count; return Count;
}
AQuestBot* AQuestBotSpawner::TrySpawnBot()
{
    const auto* Mode=Cast<AQuestGameMode>(GetWorld()->GetAuthGameMode());
    if (!bSpawning || !BotClass || GetLivingCount()>=FMath::Max(1,MaxAlive) || !Mode || !Mode->GetDirector() || !Mode->GetDirector()->IsRunActive()) return nullptr;
    LivingBots.RemoveAll([](const TWeakObjectPtr<AQuestBot>& Bot){return !Bot.IsValid() || Bot->IsDead();});
    auto* Navigation=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if (!Navigation) return nullptr;
    for (int32 Attempt=0;Attempt<12;++Attempt)
    {
        const FVector Extent=SpawnArea->GetScaledBoxExtent();
        const FVector Guess=GetActorLocation()+FVector(FMath::FRandRange(-Extent.X,Extent.X),FMath::FRandRange(-Extent.Y,Extent.Y),0);
        FNavLocation Surface;
        if (!Navigation->ProjectPointToNavigation(Guess,Surface,FVector(70,70,250))) continue;
        const FVector Location=Surface.Location+FVector(0,0,95);
        FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
        auto* Bot=GetWorld()->SpawnActor<AQuestBot>(BotClass,Location,FRotator(0,180,0),Params);
        if (!Bot) continue;
        // Reachable navigation points give varied patrols rather than a short shuttle.
        Bot->PatrolPoints.Empty();
        for (int32 Point=0;Point<4;++Point)
        {
            FNavLocation Patrol;
            if (Navigation->GetRandomReachablePointInRadius(Surface.Location,550.f,Patrol))
                Bot->PatrolPoints.Add(Patrol.Location);
        }
        if (Bot->PatrolPoints.IsEmpty()) Bot->PatrolPoints.Add(Surface.Location);
        Bot->OnDied.AddUniqueDynamic(this,&AQuestBotSpawner::HandleBotDied);
        LivingBots.Add(Bot); ++TotalSpawned; return Bot;
    }
    return nullptr;
}
void AQuestBotSpawner::HandleBotDied(AQuestBot* Victim,AActor* Killer)
{
    Victim->OnDied.RemoveDynamic(this,&AQuestBotSpawner::HandleBotDied);
    LivingBots.Remove(Victim);
    if (auto* Mode=Cast<AQuestGameMode>(GetWorld()->GetAuthGameMode()))
        if (Mode->GetDirector()) Mode->GetDirector()->NotifyBotKilled(Victim,Killer);
}
void AQuestBotSpawner::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(SpawnTimer);
    for (const auto& Bot:LivingBots) if (Bot.IsValid()) Bot->OnDied.RemoveDynamic(this,&AQuestBotSpawner::HandleBotDied);
    Super::EndPlay(Reason);
}

void AQuestGameMode::BeginPlay()
{
    Super::BeginPlay();
    for (TActorIterator<AQuestDirector> It(GetWorld());It;++It) { Director=*It;break; }
    if (!Director) return;
    Director->OnRunEnded.AddUniqueDynamic(this,&AQuestGameMode::OnRunEnded);
    Director->StartRun();
    for (TActorIterator<AQuestBotSpawner> It(GetWorld());It;++It) It->SetSpawning(true);
}
void AQuestGameMode::OnRunEnded(bool bSuccess,FText Reason)
{
    for (TActorIterator<AQuestBotSpawner> It(GetWorld());It;++It) It->SetSpawning(false);
    for (TActorIterator<AQuestBot> It(GetWorld());It;++It)
    {
        It->SetActorTickEnabled(false); It->GetCharacterMovement()->StopMovementImmediately();
        It->GetAbilitySystemComponent()->CancelAllAbilities();
        if (auto* AI=Cast<AAIController>(It->GetController())) AI->StopMovement();
    }
    if (auto* Player=Cast<AQuestPlayer>(UGameplayStatics::GetPlayerPawn(this,0))) Player->GetCharacterMovement()->DisableMovement();
}
void AQuestGameMode::RestartRun()
{
    if (!Director) return;
    auto* PC=UGameplayStatics::GetPlayerController(this,0);
    if (!PC) return;
    ++RestartCount;
    for (TActorIterator<AQuestBotSpawner> It(GetWorld());It;++It) It->SetSpawning(false);
    TArray<AQuestBot*> OldBots; for (TActorIterator<AQuestBot> It(GetWorld());It;++It) OldBots.Add(*It);
    for (auto* Bot:OldBots)
    {
        if (auto* Controller=Bot->GetController()) Controller->Destroy();
        Bot->Destroy();
    }
    APawn* OldPlayer=PC->GetPawn(); PC->UnPossess(); if (OldPlayer) OldPlayer->Destroy();
    PC->bShowMouseCursor=false; PC->SetInputMode(FInputModeGameOnly());
    Director->StartRun();
    RestartPlayer(PC); // Native character respawn, without reloading the level.
    for (TActorIterator<AQuestBotSpawner> It(GetWorld());It;++It) It->SetSpawning(true);
}

UQuestShootAbility::UQuestShootAbility()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    CooldownGameplayEffectClass=UQuestShotCooldown::StaticClass();
}
bool UQuestShootAbility::CanActivateAbility(const FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    const FGameplayTagContainer* SourceTags,const FGameplayTagContainer* TargetTags,FGameplayTagContainer* RelevantTags) const
{
    const auto* Player=Info ? Cast<AQuestPlayer>(Info->AvatarActor.Get()) : nullptr;
    return Player && Player->IsAlive() && Player->GetQuestDirector() && Player->GetQuestDirector()->IsRunActive() &&
        Super::CanActivateAbility(Handle,Info,SourceTags,TargetTags,RelevantTags);
}
void UQuestShootAbility::ActivateAbility(const FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    const FGameplayAbilityActivationInfo Activation,const FGameplayEventData* EventData)
{
    auto* Player=Cast<AQuestPlayer>(Info->AvatarActor.Get());
    if (!Player || !CommitAbility(Handle,Info,Activation)) { EndAbility(Handle,Info,Activation,true,true);return; }
    ++Player->ShotsFired;
    FHitResult AimHit; Player->TraceAim(AimHit);
    const FVector AimEnd=AimHit.bBlockingHit ? AimHit.ImpactPoint : Player->FollowCamera->GetComponentLocation()+Player->FollowCamera->GetForwardVector()*6000.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(QuestShot),false,Player);
    FHitResult ActualHit;
    GetWorld()->LineTraceSingleByChannel(ActualHit,Player->GetShotStart(),AimEnd+((AimEnd-Player->GetShotStart()).GetSafeNormal()*10.f),ECC_Visibility,Query);
    FGameplayCueParameters Cue; Cue.Location=ActualHit.bBlockingHit ? ActualHit.ImpactPoint : AimEnd;
    Player->AbilitySystem->ExecuteGameplayCue(TAG_QuestShotCue,Cue);
    if (auto* Bot=Cast<AQuestBot>(ActualHit.GetActor()); Bot && !Bot->IsDead() && Player->ShotDamageEffect)
    {
        auto Context=Player->AbilitySystem->MakeEffectContext();Context.AddHitResult(ActualHit);
        auto Spec=Player->AbilitySystem->MakeOutgoingSpec(Player->ShotDamageEffect,1.f,Context);
        if (Spec.IsValid()) { Player->AbilitySystem->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(),Bot->GetAbilitySystemComponent());++Player->Hits; }
    }
    EndAbility(Handle,Info,Activation,true,false);
}
UQuestDamageEffect::UQuestDamageEffect()
{
    DurationPolicy=EGameplayEffectDurationType::Instant;
    FGameplayModifierInfo Modifier;Modifier.Attribute=UCombatAttributeSet::GetHealthAttribute();
    Modifier.ModifierOp=EGameplayModOp::Additive;Modifier.ModifierMagnitude=FScalableFloat(-25.f);Modifiers.Add(Modifier);
}
UQuestShotCooldown::UQuestShotCooldown()
{
    DurationPolicy=EGameplayEffectDurationType::HasDuration;DurationMagnitude=FScalableFloat(.35f);
    auto* Component=CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("QuestShotCooldownTags"));
    GEComponents.Add(Component);FInheritedTagContainer Changes;Changes.AddTag(TAG_QuestShotCooldown);Component->SetAndApplyTargetTagChanges(Changes);
}
UQuestShotCue::UQuestShotCue() { GameplayCueTag=TAG_QuestShotCue;GameplayCueName=GameplayCueTag.GetTagName(); }
bool UQuestShotCue::OnExecute_Implementation(AActor* TargetActor,const FGameplayCueParameters& Parameters) const
{
    if (auto* Player=Cast<AQuestPlayer>(TargetActor)) { Player->PresentShot(Parameters.Location);return true; } return false;
}
