#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "QuestHUD.generated.h"

class UProgressBar;
class UTextBlock;
class UBorder;
class UButton;
class AQuestPlayer;
class AQuestDirector;
struct FOnAttributeChangeData;

UCLASS(Blueprintable)
class QUESTPRACTICE_API UQuestHUD : public UUserWidget
{
    GENERATED_BODY()
public:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry,float DeltaSeconds) override;
    UFUNCTION(BlueprintPure,Category="Quest UI") FString GetDisplayedProgress() const;
    UFUNCTION(BlueprintPure,Category="Quest UI") bool IsResultVisible() const;
    UFUNCTION(BlueprintPure,Category="Quest UI") FString GetDisplayedResult() const;
    UFUNCTION(BlueprintPure,Category="Quest UI") float GetDisplayedHealth() const;
    UFUNCTION(BlueprintCallable,Category="Quest UI") void Replay();
private:
    UFUNCTION() void RefreshQuest();
    void HealthChanged(const FOnAttributeChangeData& Change);
    void UpdateHealth();
    UPROPERTY() TObjectPtr<UProgressBar> HealthBar;
    UPROPERTY() TObjectPtr<UTextBlock> HealthText;
    UPROPERTY() TObjectPtr<UTextBlock> QuestText;
    UPROPERTY() TObjectPtr<UTextBlock> ProgressText;
    UPROPERTY() TObjectPtr<UTextBlock> TimerText;
    UPROPERTY() TObjectPtr<UBorder> ResultPanel;
    UPROPERTY() TObjectPtr<UTextBlock> ResultTitle;
    UPROPERTY() TObjectPtr<UTextBlock> ResultDescription;
    UPROPERTY() TObjectPtr<UButton> ReplayButton;
    TWeakObjectPtr<AQuestPlayer> Player;
    TWeakObjectPtr<AQuestDirector> Director;
    FDelegateHandle HealthDelegate;
    bool bResultShown = false;
};
