using UnrealBuildTool;
public class StealthShooterEditorTarget : TargetRules
{
    public StealthShooterEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("StealthShooter");
    }
}
