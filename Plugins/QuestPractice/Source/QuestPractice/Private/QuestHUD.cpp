#include "QuestHUD.h"
#include "QuestCombat.h"
#include "QuestSystem.h"
#include "CombatAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"
#include "Components/Button.h"
#include "Components/SizeBox.h"
#include "GameFramework/PlayerController.h"

void UQuestHUD::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    auto* Canvas=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=Canvas;
    auto Panel=[&](FVector2D Position,FVector2D Size,FAnchors Anchors,FVector2D Alignment)
    {
        auto* Border=WidgetTree->ConstructWidget<UBorder>();Border->SetBrushColor(FLinearColor(.012f,.025f,.04f,.94f));Border->SetPadding(FMargin(22.f));
        auto* Entry=Canvas->AddChildToCanvas(Border);Entry->SetAnchors(Anchors);Entry->SetAlignment(Alignment);Entry->SetPosition(Position);Entry->SetSize(Size);
        return Border;
    };
    auto Stack=[&](UBorder* Border){auto* Box=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Box);return Box;};
    auto Text=[&](UVerticalBox* Box,const TCHAR* Value,int32 Size,FLinearColor Color)
    {
        auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Value));Label->SetColorAndOpacity(FSlateColor(Color));
        FSlateFontInfo Font=Label->GetFont();Font.Size=Size;Label->SetFont(Font);Label->SetAutoWrapText(true);
        Box->AddChildToVerticalBox(Label)->SetPadding(FMargin(0,0,0,9));return Label;
    };
    auto* HealthStack=Stack(Panel(FVector2D(26,26),FVector2D(360,130),FAnchors(0,0),FVector2D::ZeroVector));
    Text(HealthStack,TEXT("12.7  /  ЗАЧИСТКА СЕКТОРА"),16,FLinearColor(.3f,.8f,1.f));
    HealthText=Text(HealthStack,TEXT("Здоровье: 100 / 100"),24,FLinearColor::White);
    auto* BarBox=WidgetTree->ConstructWidget<USizeBox>();BarBox->SetHeightOverride(15.f);
    HealthBar=WidgetTree->ConstructWidget<UProgressBar>();HealthBar->SetFillColorAndOpacity(FLinearColor(.12f,.8f,.5f));
    BarBox->SetContent(HealthBar);HealthStack->AddChildToVerticalBox(BarBox);

    auto* QuestStack=Stack(Panel(FVector2D(-26,26),FVector2D(440,205),FAnchors(1,0),FVector2D(1,0)));
    Text(QuestStack,TEXT("ТЕКУЩЕЕ ЗАДАНИЕ"),16,FLinearColor(.3f,.8f,1.f));
    QuestText=Text(QuestStack,TEXT("Уничтожить ботов"),24,FLinearColor::White);
    ProgressText=Text(QuestStack,TEXT("Уничтожено ботов: 0 / 3"),22,FLinearColor(1.f,.75f,.3f));
    TimerText=Text(QuestStack,TEXT(""),18,FLinearColor(.7f,.8f,.9f));

    auto* Crosshair=WidgetTree->ConstructWidget<UTextBlock>();Crosshair->SetText(FText::FromString(TEXT("+")));
    FSlateFontInfo CrosshairFont=Crosshair->GetFont();CrosshairFont.Size=30;Crosshair->SetFont(CrosshairFont);
    Crosshair->SetColorAndOpacity(FSlateColor(FLinearColor(1.f,.65f,.15f)));
    auto* CrosshairSlot=Canvas->AddChildToCanvas(Crosshair);CrosshairSlot->SetAnchors(FAnchors(.5f,.5f));
    CrosshairSlot->SetAlignment(FVector2D(.5f,.5f));CrosshairSlot->SetAutoSize(true);
    auto* Help=WidgetTree->ConstructWidget<UTextBlock>();Help->SetText(FText::FromString(TEXT("ЛКМ — выстрел  ·  WASD — движение  ·  R — заново")));
    FSlateFontInfo HelpFont=Help->GetFont();HelpFont.Size=18;Help->SetFont(HelpFont);
    auto* HelpSlot=Canvas->AddChildToCanvas(Help);HelpSlot->SetAnchors(FAnchors(.5f,1.f));HelpSlot->SetAlignment(FVector2D(.5f,1.f));HelpSlot->SetPosition(FVector2D(0,-25));HelpSlot->SetAutoSize(true);

    ResultPanel=Panel(FVector2D::ZeroVector,FVector2D(660,350),FAnchors(.5f,.5f),FVector2D(.5f,.5f));
    ResultPanel->SetBrushColor(FLinearColor(.015f,.03f,.05f,.99f));ResultPanel->SetPadding(FMargin(35.f));
    auto* ResultStack=Stack(ResultPanel);
    ResultTitle=Text(ResultStack,TEXT(""),32,FLinearColor::White);
    ResultDescription=Text(ResultStack,TEXT(""),23,FLinearColor(.85f,.9f,1.f));
    ReplayButton=WidgetTree->ConstructWidget<UButton>();
    auto* ReplayText=WidgetTree->ConstructWidget<UTextBlock>();ReplayText->SetText(FText::FromString(TEXT("Попробовать ещё раз")));
    FSlateFontInfo ReplayFont=ReplayText->GetFont();ReplayFont.Size=24;ReplayText->SetFont(ReplayFont);ReplayText->SetColorAndOpacity(FSlateColor(FLinearColor(.02f,.035f,.05f)));
    ReplayButton->SetContent(ReplayText);ReplayButton->SetBackgroundColor(FLinearColor(.25f,.8f,1.f));
    ResultStack->AddChildToVerticalBox(ReplayButton)->SetPadding(FMargin(0,20,0,0));
    ResultPanel->SetVisibility(ESlateVisibility::Collapsed);
}
void UQuestHUD::NativeConstruct()
{
    Super::NativeConstruct();Player=Cast<AQuestPlayer>(GetOwningPlayerPawn());
    if (Player.IsValid())
    {
        HealthDelegate=Player->AbilitySystem->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).AddUObject(this,&UQuestHUD::HealthChanged);
        Director=Player->GetQuestDirector();
    }
    if (Director.IsValid()) Director->OnUpdated.AddUniqueDynamic(this,&UQuestHUD::RefreshQuest);
    ReplayButton->OnClicked.AddUniqueDynamic(this,&UQuestHUD::Replay);
    UpdateHealth();RefreshQuest();
}
void UQuestHUD::NativeDestruct()
{
    if (Director.IsValid()) Director->OnUpdated.RemoveDynamic(this,&UQuestHUD::RefreshQuest);
    if (Player.IsValid()) Player->AbilitySystem->GetGameplayAttributeValueChangeDelegate(UCombatAttributeSet::GetHealthAttribute()).Remove(HealthDelegate);
    Super::NativeDestruct();
}
void UQuestHUD::HealthChanged(const FOnAttributeChangeData& Change) { UpdateHealth(); }
void UQuestHUD::UpdateHealth()
{
    if (!Player.IsValid()) return;
    HealthText->SetText(FText::FromString(FString::Printf(TEXT("Здоровье: %.0f / %.0f"),Player->GetHealth(),Player->GetMaxHealth())));
    HealthBar->SetPercent(Player->GetHealth()/FMath::Max(1.f,Player->GetMaxHealth()));
    HealthBar->SetFillColorAndOpacity(Player->GetHealth()>30.f ? FLinearColor(.12f,.8f,.5f) : FLinearColor(1.f,.15f,.08f));
}
void UQuestHUD::RefreshQuest()
{
    if (!Director.IsValid() && Player.IsValid())
    {
        Director=Player->GetQuestDirector();
        if (Director.IsValid()) Director->OnUpdated.AddUniqueDynamic(this,&UQuestHUD::RefreshQuest);
    }
    if (!Director.IsValid()) return;
    if (!Director->bFinished)
    {
        bResultShown=false;
        ResultPanel->SetVisibility(ESlateVisibility::Collapsed);
    }
    const auto* Quest=Director->GetActiveQuest();
    if (Quest)
    {
        QuestText->SetText(Quest->Title);ProgressText->SetText(Quest->GetProgressText());
        ProgressText->SetColorAndOpacity(FSlateColor(Quest->State==EQuestState::Completed ? FLinearColor(.2f,1.f,.55f) : Quest->State==EQuestState::Failed ? FLinearColor(1.f,.3f,.15f) : FLinearColor(1.f,.75f,.3f)));
    }
    if (Director->bFinished && !bResultShown)
    {
        bResultShown=true;
        ResultTitle->SetText(FText::FromString(Director->bSucceeded ? TEXT("ЗАДАНИЕ ВЫПОЛНЕНО") : TEXT("ЗАДАНИЕ ПРОВАЛЕНО")));
        ResultTitle->SetColorAndOpacity(FSlateColor(Director->bSucceeded ? FLinearColor(.2f,1.f,.55f) : FLinearColor(1.f,.3f,.15f)));
        ResultDescription->SetText(FText::FromString(Director->ResultReason.ToString()+TEXT("\n")+(Quest ? Quest->GetProgressText().ToString() : TEXT(""))));
        ResultPanel->SetVisibility(ESlateVisibility::Visible);
        if (auto* PC=GetOwningPlayer())
        {
            PC->bShowMouseCursor=true;
            FInputModeGameAndUI Mode;Mode.SetWidgetToFocus(ReplayButton->TakeWidget());Mode.SetHideCursorDuringCapture(false);PC->SetInputMode(Mode);
        }
    }
}
void UQuestHUD::NativeTick(const FGeometry& Geometry,float DeltaSeconds)
{
    Super::NativeTick(Geometry,DeltaSeconds);
    if (!Director.IsValid()) RefreshQuest();
    if (Director.IsValid())
        if (const auto* Quest=Director->GetActiveQuest())
            TimerText->SetText(FText::FromString(Director->bFinished ? TEXT("Раунд завершён") : FString::Printf(TEXT("Осталось: %d с"),FMath::CeilToInt(Quest->GetRemainingSeconds()))));
}
void UQuestHUD::Replay() { if (Player.IsValid()) Player->RestartQuestRun(); }
FString UQuestHUD::GetDisplayedProgress() const { return ProgressText ? ProgressText->GetText().ToString() : FString(); }
bool UQuestHUD::IsResultVisible() const { return ResultPanel && ResultPanel->GetVisibility()==ESlateVisibility::Visible; }
FString UQuestHUD::GetDisplayedResult() const { return ResultTitle ? ResultTitle->GetText().ToString() : FString(); }
float UQuestHUD::GetDisplayedHealth() const { return HealthBar ? HealthBar->GetPercent() : -1.f; }
