using UnrealBuildTool;

public class CombatGAS : ModuleRules
{
    public CombatGAS(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "GameplayAbilities", "GameplayTags",
            "GameplayTasks", "AIModule", "NavigationSystem", "UMG", "InputCore"
        });
        PrivateDependencyModuleNames.AddRange(new[] { "Slate", "SlateCore" });
    }
}
