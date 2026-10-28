using UnrealBuildTool;
public class QuestPractice : ModuleRules
{
    public QuestPractice(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "CombatGAS", "GameplayAbilities", "GameplayTags",
            "GameplayTasks", "AIModule", "NavigationSystem", "UMG", "InputCore"
        });
        PrivateDependencyModuleNames.AddRange(new[] { "Slate", "SlateCore", "AssetRegistry" });
    }
}
