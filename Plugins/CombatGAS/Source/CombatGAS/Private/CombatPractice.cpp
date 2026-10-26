#include "CombatPractice.h"
#include "CombatAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystemGlobals.h"
#include "GameplayCueManager.h"
#include "GameplayCueSet.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
#include "NativeGameplayTags.h"
#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/InputComponent.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/Border.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Blueprint/WidgetTree.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "UObject/ConstructorHelpers.h"

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShotCooldown, "Cooldown.Bot.Shoot");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShotCue, "GameplayCue.Bot.Shoot");

ACombatPlayer::ACombatPlayer()
{
    GetCapsuleComponent()->InitCapsuleSize(35.f, 90.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    AbilitySystem = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystem"));
    Attributes = CreateDefaultSubobject<UCombatAttributeSet>(TEXT("Attributes"));
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 420.f;
    CameraBoom->bUsePawnControlRotation = true;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->MaxWalkSpeed = 450.f;
    GetCharacterMovement()->JumpZVelocity = 500.f;
    GetMesh()->SetRelativeLocation(FVector(0,0,-90));
    GetMesh()->SetRelativeRotation(FRotator(0,-90,0));
}

void ACombatPlayer::BeginPlay()
{
    Super::BeginPlay();
    AbilitySystem->InitAbilityActorInfo(this, this);
    AbilitySystem->AddAttributeSetSubobject(Attributes.Get());
    AbilitySystem->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute())
        .AddUObject(this, &ACombatPlayer::HealthChanged);
    if (IsLocallyControlled() && HUDClass)
    {
        HUD = CreateWidget<UUserWidget>(Cast<APlayerController>(GetController()), HUDClass);
        if (HUD) HUD->AddToViewport();
    }
}

void ACombatPlayer::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis(TEXT("CombatForward"), this, &ACombatPlayer::MoveForward);
    Input->BindAxis(TEXT("CombatRight"), this, &ACombatPlayer::MoveRight);
    Input->BindAxis(TEXT("CombatTurn"), this, &ACombatPlayer::AddControllerYawInput);
    Input->BindAxis(TEXT("CombatLook"), this, &ACombatPlayer::AddControllerPitchInput);
    Input->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ACombatPlayer::Jump);
    Input->BindKey(EKeys::SpaceBar, IE_Released, this, &ACombatPlayer::StopJumping);
    Input->BindKey(EKeys::R, IE_Pressed, this, &ACombatPlayer::RestartPractice);
}

void ACombatPlayer::MoveForward(float Value)
{
    if (Controller && IsAlive()) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::X),Value);
}
void ACombatPlayer::MoveRight(float Value)
{
    if (Controller && IsAlive()) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::Y),Value);
}
float ACombatPlayer::GetHealth() const { return Attributes->GetHealth(); }
float ACombatPlayer::GetMaxHealth() const { return Attributes->GetMaxHealth(); }
bool ACombatPlayer::IsAlive() const { return GetHealth() > 0.f; }
void ACombatPlayer::HealthChanged(const FOnAttributeChangeData& Change)
{
    if (Change.NewValue <= 0.f) GetCharacterMovement()->DisableMovement();
}
void ACombatPlayer::RestartPractice()
{
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}

ACombatBot::ACombatBot()
{
    PrimaryActorTick.bCanEverTick = true;
    AIControllerClass = AAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    GetCapsuleComponent()->InitCapsuleSize(35.f,90.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    AbilitySystem = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystem"));
    GetMesh()->SetRelativeLocation(FVector(0,0,-90));
    GetMesh()->SetRelativeRotation(FRotator(0,-90,0));
    GetCharacterMovement()->MaxWalkSpeed = 150.f;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    bUseControllerRotationYaw = false;

    WeaponRoot = CreateDefaultSubobject<USceneComponent>(TEXT("WeaponRoot"));
    WeaponRoot->SetupAttachment(RootComponent);
    WeaponBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WeaponBody"));
    WeaponBody->SetupAttachment(WeaponRoot);
    WeaponBarrel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WeaponBarrel"));
    WeaponBarrel->SetupAttachment(WeaponRoot);
    Muzzle = CreateDefaultSubobject<USceneComponent>(TEXT("Muzzle"));
    Muzzle->SetupAttachment(WeaponRoot);
    Muzzle->SetRelativeLocation(FVector(70,0,0));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    WeaponBody->SetStaticMesh(Cube.Object);
    WeaponBody->SetRelativeScale3D(FVector(.45,.085,.14));
    WeaponBarrel->SetStaticMesh(Cylinder.Object);
    WeaponBarrel->SetRelativeLocation(FVector(45,0,0));
    WeaponBarrel->SetRelativeRotation(FRotator(90,0,0));
    WeaponBarrel->SetRelativeScale3D(FVector(.035,.035,.5));
    for (auto* Part : {WeaponBody.Get(),WeaponBarrel.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
    }
}

void ACombatBot::BeginPlay()
{
    Super::BeginPlay();
    AbilitySystem->InitAbilityActorInfo(this,this);
    // An explicit asset reference keeps the cue in cooked builds and registers it deterministically.
    // Execution still travels through ASC -> GameplayCueManager -> GC_Bot_Shoot.OnExecute.
    if (ShotCue)
    {
        auto* CueSet=UAbilitySystemGlobals::Get().GetGameplayCueManager()->GetRuntimeCueSet();
        CueSet->AddCues({FGameplayCueReferencePair(TAG_ShotCue,FSoftObjectPath(ShotCue.Get()))});
    }
    if (HasAuthority() && ShootAbility) AbilitySystem->GiveAbility(FGameplayAbilitySpec(ShootAbility,1));
    Target = Cast<ACombatPlayer>(UGameplayStatics::GetPlayerPawn(this,0));
    if (PatrolPoints.IsEmpty())
    {
        PatrolPoints.Add(GetActorLocation());
        PatrolPoints.Add(GetActorLocation()+FVector(0,400,0));
    }
    SetWeaponDrawn(false);
}

bool ACombatBot::HasLineOfSight() const
{
    if (!Target || !Target->IsAlive()) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BotSight),false,this);
    const FVector Eye=GetActorLocation()+FVector(0,0,60);
    const FVector Aim=Target->GetActorLocation()+FVector(0,0,25);
    GetWorld()->LineTraceSingleByChannel(Hit,Eye,Aim,ECC_Visibility,Params);
    return !Hit.bBlockingHit || Hit.GetActor()==Target;
}

bool ACombatBot::CanSeePlayer() const
{
    if (!Target || !Target->IsAlive()) return false;
    const FVector Offset=Target->GetActorLocation()-GetActorLocation();
    if (Offset.SizeSquared()>FMath::Square(SightRadius)) return false;
    // Keep sight once the bot is facing the target; the initial detection respects the vision cone.
    const float Facing=FVector::DotProduct(GetActorForwardVector(),Offset.GetSafeNormal2D());
    return Facing>=FMath::Cos(FMath::DegreesToRadians(PeripheralVisionDegrees)) && HasLineOfSight();
}

void ACombatBot::SetWeaponDrawn(bool bDrawn)
{
    bWeaponDrawn=bDrawn;
    WeaponRoot->AttachToComponent(GetMesh(),FAttachmentTransformRules::SnapToTargetNotIncludingScale,
        bDrawn ? FName(TEXT("hand_r")) : FName(TEXT("spine_03")));
    WeaponRoot->SetRelativeLocation(bDrawn ? FVector(12,0,0) : FVector(-18,25,-20));
    WeaponRoot->SetRelativeRotation(bDrawn ? FRotator::ZeroRotator : FRotator(70,0,0));
}

void ACombatBot::UpdatePatrol()
{
    auto* AI=Cast<AAIController>(GetController());
    if (!AI || PatrolPoints.IsEmpty()) return;
    GetCharacterMovement()->bOrientRotationToMovement=true;
    if (AI->GetMoveStatus()!=EPathFollowingStatus::Moving)
    {
        if (FVector::Dist2D(GetActorLocation(),PatrolPoints[PatrolIndex])<80.f)
            PatrolIndex=(PatrolIndex+1)%PatrolPoints.Num();
        AI->MoveToLocation(PatrolPoints[PatrolIndex],40.f,true,true,false,true);
    }
}

void ACombatBot::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority()) return;
    if (!Target) Target=Cast<ACombatPlayer>(UGameplayStatics::GetPlayerPawn(this,0));
    const float Now=GetWorld()->GetTimeSeconds();
    if (CanSeePlayer())
    {
        LostSightTime=0.f;
        if (State==ECombatBotState::Patrol)
        {
            State=ECombatBotState::DrawingWeapon;
            DrawStartedAt=Now;
            SetWeaponDrawn(true);
        }
        if (auto* AI=Cast<AAIController>(GetController())) AI->StopMovement();
        GetCharacterMovement()->bOrientRotationToMovement=false;
        const FVector Delta=Target->GetActorLocation()-GetActorLocation();
        const FRotator Aim(0,Delta.Rotation().Yaw,0);
        SetActorRotation(FMath::RInterpTo(GetActorRotation(),Aim,DeltaSeconds,8.f));
        WeaponRoot->SetWorldRotation((Target->GetActorLocation()+FVector(0,0,25)-WeaponRoot->GetComponentLocation()).Rotation());
        if (Now-DrawStartedAt>=DrawWeaponDuration)
        {
            State=ECombatBotState::Combat;
            RequestShot(); // The Gameplay Effect cooldown, not a timer, decides when another shot is allowed.
        }
    }
    else if (State!=ECombatBotState::Patrol)
    {
        State=ECombatBotState::Searching;
        if (LostSightTime==0.f) LostSightTime=Now;
        if (Now-LostSightTime>=ForgetDelay)
        {
            State=ECombatBotState::Patrol;
            SetWeaponDrawn(false);
            UpdatePatrol();
        }
    }
    else UpdatePatrol();
}

bool ACombatBot::CanShootTarget() const
{
    return State==ECombatBotState::Combat && bWeaponDrawn && CanSeePlayer();
}
bool ACombatBot::RequestShot()
{
    return ShootAbility && AbilitySystem->TryActivateAbilityByClass(ShootAbility);
}
FVector ACombatBot::GetMuzzleLocation() const { return Muzzle->GetComponentLocation(); }
float ACombatBot::GetShotCooldownRemaining() const
{
    FGameplayTagContainer CooldownTags(TAG_ShotCooldown);
    const FGameplayEffectQuery Query=FGameplayEffectQuery::MakeQuery_MatchAnyOwningTags(CooldownTags);
    float Remaining=0.f;
    for (float Value : AbilitySystem->GetActiveEffectsTimeRemaining(Query)) Remaining=FMath::Max(Remaining,Value);
    return Remaining;
}

void ACombatBot::PresentShot(const FVector& End)
{
    ++CueCount;
    if (auto* Visual=GetWorld()->SpawnActor<ACombatShotVisual>())
        Visual->Initialize(GetMuzzleLocation(),End,TracerMaterial);
    if (ShotSound) UGameplayStatics::PlaySoundAtLocation(this,ShotSound,GetMuzzleLocation(),.5f);
}

UCombatShootAbility::UCombatShootAbility()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    CooldownGameplayEffectClass=UCombatShotCooldown::StaticClass();
}

bool UCombatShootAbility::CanActivateAbility(const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags,
    const FGameplayTagContainer* TargetTags, FGameplayTagContainer* RelevantTags) const
{
    const auto* Bot=ActorInfo ? Cast<ACombatBot>(ActorInfo->AvatarActor.Get()) : nullptr;
    return Bot && Bot->CanShootTarget() && Super::CanActivateAbility(Handle,ActorInfo,SourceTags,TargetTags,RelevantTags);
}

void UCombatShootAbility::ActivateAbility(const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo,
    const FGameplayEventData* TriggerEventData)
{
    auto* Bot=Cast<ACombatBot>(ActorInfo->AvatarActor.Get());
    if (!Bot || !Bot->CanShootTarget() || !CommitAbility(Handle,ActorInfo,ActivationInfo))
    {
        EndAbility(Handle,ActorInfo,ActivationInfo,true,true);
        return;
    }
    ++Bot->ShotCount;
    Bot->ShotTimes.Add(GetWorld()->GetTimeSeconds());
    const FVector Start=Bot->GetMuzzleLocation();
    const FVector Aim=Bot->Target->GetActorLocation()+FVector(0,0,25);
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BotShot),false,Bot);
    // A weapon protruding into cover must not allow the shot to start on the far side of it.
    const FVector Shoulder=Bot->GetActorLocation()+FVector(0,0,45);
    const bool bBarrelBlocked=GetWorld()->LineTraceSingleByChannel(Hit,Shoulder,Start,ECC_Visibility,Params);
    if (!bBarrelBlocked) GetWorld()->LineTraceSingleByChannel(Hit,Start,Aim,ECC_Visibility,Params);
    const FVector End=Hit.bBlockingHit ? Hit.ImpactPoint : Aim;
    FGameplayCueParameters Cue;
    Cue.Location=End;
    Cue.Instigator=Bot;
    Bot->AbilitySystem->ExecuteGameplayCue(TAG_ShotCue,Cue);
    // A blocking wall consumes the shot/cooldown but never damages the player behind it.
    if (Hit.GetActor()==Bot->Target && Bot->DamageEffect)
    {
        FGameplayEffectContextHandle Context=Bot->AbilitySystem->MakeEffectContext();
        Context.AddHitResult(Hit);
        FGameplayEffectSpecHandle Spec=Bot->AbilitySystem->MakeOutgoingSpec(Bot->DamageEffect,1.f,Context);
        if (Spec.IsValid())
        {
            Bot->AbilitySystem->ApplyGameplayEffectSpecToTarget(*Spec.Data.Get(),Bot->Target->GetAbilitySystemComponent());
            ++Bot->HitCount;
        }
    }
    EndAbility(Handle,ActorInfo,ActivationInfo,true,false);
}

UCombatDamageEffect::UCombatDamageEffect()
{
    DurationPolicy=EGameplayEffectDurationType::Instant;
    FGameplayModifierInfo Modifier;
    Modifier.Attribute=UCombatAttributeSet::GetHealthAttribute();
    Modifier.ModifierOp=EGameplayModOp::Additive;
    Modifier.ModifierMagnitude=FScalableFloat(-10.f);
    Modifiers.Add(Modifier);
}

UCombatShotCooldown::UCombatShotCooldown()
{
    DurationPolicy=EGameplayEffectDurationType::HasDuration;
    DurationMagnitude=FScalableFloat(1.25f);
    auto* TagComponent=CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("ShotCooldownTags"));
    GEComponents.Add(TagComponent);
    FInheritedTagContainer Changes;
    Changes.AddTag(TAG_ShotCooldown);
    TagComponent->SetAndApplyTargetTagChanges(Changes);
}

UCombatShotCue::UCombatShotCue()
{
    GameplayCueTag=TAG_ShotCue;
    GameplayCueName=GameplayCueTag.GetTagName();
}
bool UCombatShotCue::OnExecute_Implementation(AActor* MyTarget,const FGameplayCueParameters& Parameters) const
{
    if (auto* Bot=Cast<ACombatBot>(MyTarget)) { Bot->PresentShot(Parameters.Location); return true; }
    return false;
}

ACombatShotVisual::ACombatShotVisual()
{
    PrimaryActorTick.bCanEverTick=false;
    InitialLifeSpan=.10f;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Tracer=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Tracer"));
    Flash=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MuzzleFlash"));
    Tracer->SetupAttachment(RootComponent);
    Flash->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    Tracer->SetStaticMesh(Cube.Object);
    Flash->SetStaticMesh(Sphere.Object);
    for (auto* Part : {Tracer.Get(),Flash.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCastShadow(false);
    }
}
void ACombatShotVisual::Initialize(const FVector& Start,const FVector& End,UMaterialInterface* Material)
{
    const FVector Delta=End-Start;
    Tracer->SetWorldLocation((Start+End)*.5f);
    Tracer->SetWorldRotation(Delta.Rotation());
    Tracer->SetWorldScale3D(FVector(Delta.Size()/100.f,.012f,.012f));
    Flash->SetWorldLocation(Start);
    Flash->SetWorldScale3D(FVector(.12f,.08f,.08f));
    if (Material) { Tracer->SetMaterial(0,Material); Flash->SetMaterial(0,Material); }
}

void UCombatHUD::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    if (!HealthBar)
    {
        auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();
        WidgetTree->RootWidget=Canvas;
        auto* Panel=WidgetTree->ConstructWidget<UBorder>();
        Panel->SetBrushColor(FLinearColor(.015f,.025f,.045f,.92f));
        Panel->SetPadding(FMargin(22.f));
        auto* PanelSlot=Canvas->AddChildToCanvas(Panel);
        PanelSlot->SetPosition(FVector2D(28,28)); PanelSlot->SetSize(FVector2D(520,220));
        auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();
        Panel->SetContent(Stack);
        auto AddText=[&](const FString& Text,int32 Size,FLinearColor Color)
        {
            auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
            Label->SetText(FText::FromString(Text));
            FSlateFontInfo Font=Label->GetFont(); Font.Size=Size; Label->SetFont(Font);
            Label->SetColorAndOpacity(FSlateColor(Color));
            Stack->AddChildToVerticalBox(Label)->SetPadding(FMargin(0,0,0,10));
            return Label;
        };
        AddText(TEXT("10.5  |  COMBAT / GAMEPLAY ABILITIES"),16,FLinearColor(.4f,.8f,1.f));
        HealthText=AddText(TEXT(""),24,FLinearColor::White);
        HealthBar=WidgetTree->ConstructWidget<UProgressBar>();
        HealthBar->SetFillColorAndOpacity(FLinearColor(.12f,.8f,.45f));
        auto* BarSlot=Stack->AddChildToVerticalBox(HealthBar);
        BarSlot->SetPadding(FMargin(0,0,0,12));
        BotText=AddText(TEXT(""),14,FLinearColor(.8f,.85f,.95f));
        AddText(TEXT("WASD - move   |   Mouse - look   |   R - restart"),13,FLinearColor(.6f,.65f,.75f));
    }
}
void UCombatHUD::NativeConstruct()
{
    Super::NativeConstruct();
    Player=Cast<ACombatPlayer>(GetOwningPlayerPawn());
    if (Player.IsValid())
    {
        auto* ASC=Player->GetAbilitySystemComponent();
        HealthHandle=ASC->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).AddUObject(this,&UCombatHUD::RefreshHealth);
        MaxHealthHandle=ASC->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetMaxHealthAttribute()).AddUObject(this,&UCombatHUD::RefreshHealth);
    }
    UpdateHealth();
    SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UCombatHUD::NativeDestruct()
{
    if (Player.IsValid())
    {
        auto* ASC=Player->GetAbilitySystemComponent();
        ASC->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).Remove(HealthHandle);
        ASC->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetMaxHealthAttribute()).Remove(MaxHealthHandle);
    }
    Super::NativeDestruct();
}
void UCombatHUD::RefreshHealth(const FOnAttributeChangeData& Change) { UpdateHealth(); }
void UCombatHUD::UpdateHealth()
{
    if (!Player.IsValid() || !HealthBar || !HealthText) return;
    const float Health=Player->GetHealth();
    HealthBar->SetPercent(Health/FMath::Max(1.f,Player->GetMaxHealth()));
    HealthBar->SetFillColorAndOpacity(Health>30.f ? FLinearColor(.12f,.8f,.45f) : FLinearColor(1.f,.2f,.12f));
    HealthText->SetText(FText::FromString(FString::Printf(TEXT("HEALTH  %.0f / %.0f%s"),Health,Player->GetMaxHealth(),Health<=0.f ? TEXT("  |  R TO RESTART") : TEXT(""))));
}
float UCombatHUD::GetDisplayedHealthPercent() const { return HealthBar ? HealthBar->GetPercent() : -1.f; }
void UCombatHUD::NativeTick(const FGeometry& Geometry,float DeltaSeconds)
{
    Super::NativeTick(Geometry,DeltaSeconds);
    if (!BotText) return;
    for (TActorIterator<ACombatBot> It(GetWorld()); It; ++It)
    {
        const auto* Bot=*It;
        const TCHAR* State=Bot->State==ECombatBotState::Patrol ? TEXT("PATROL / WEAPON HOLSTERED") :
            Bot->State==ECombatBotState::DrawingWeapon ? TEXT("TARGET DETECTED / DRAWING") :
            Bot->State==ECombatBotState::Searching ? TEXT("SIGHT LOST / SEARCHING") : TEXT("COMBAT / AIMING");
        BotText->SetText(FText::FromString(FString::Printf(TEXT("%s\nShots: %d   |   GE cooldown: %.2f s"),State,Bot->ShotCount,Bot->GetShotCooldownRemaining())));
        break;
    }
}
