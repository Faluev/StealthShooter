#pragma once

#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "CombatAttributeSet.generated.h"

#define COMBAT_ATTRIBUTE_ACCESSORS(Property) \
    GAMEPLAYATTRIBUTE_PROPERTY_GETTER(UCombatAttributeSet, Property) \
    GAMEPLAYATTRIBUTE_VALUE_GETTER(Property) \
    GAMEPLAYATTRIBUTE_VALUE_SETTER(Property) \
    GAMEPLAYATTRIBUTE_VALUE_INITTER(Property)

/** Health is changed by Gameplay Effects, never by a parallel health variable. */
UCLASS()
class COMBATGAS_API UCombatAttributeSet : public UAttributeSet
{
    GENERATED_BODY()
public:
    UCombatAttributeSet();

    UPROPERTY(BlueprintReadOnly, Category="Attributes")
    FGameplayAttributeData Health;
    COMBAT_ATTRIBUTE_ACCESSORS(Health)

    UPROPERTY(BlueprintReadOnly, Category="Attributes")
    FGameplayAttributeData MaxHealth;
    COMBAT_ATTRIBUTE_ACCESSORS(MaxHealth)

    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
    virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;
};
