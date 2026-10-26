#include "CombatAttributeSet.h"
#include "GameplayEffectExtension.h"

UCombatAttributeSet::UCombatAttributeSet()
{
    InitMaxHealth(100.f);
    InitHealth(100.f);
}

void UCombatAttributeSet::PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue)
{
    Super::PreAttributeChange(Attribute, NewValue);
    if (Attribute == GetMaxHealthAttribute()) NewValue = FMath::Max(1.f, NewValue);
    if (Attribute == GetHealthAttribute()) NewValue = FMath::Clamp(NewValue, 0.f, GetMaxHealth());
}

void UCombatAttributeSet::PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data)
{
    Super::PostGameplayEffectExecute(Data);
    if (Data.EvaluatedData.Attribute == GetHealthAttribute() || Data.EvaluatedData.Attribute == GetMaxHealthAttribute())
    {
        SetMaxHealth(FMath::Max(1.f, GetMaxHealth()));
        SetHealth(FMath::Clamp(GetHealth(), 0.f, GetMaxHealth()));
    }
}
