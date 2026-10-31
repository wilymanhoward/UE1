// See LSMainMenuWidget.h for this class's purpose and connections.

#include "LSMainMenuWidget.h"

#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "LSControlsWidget.h"
#include "LSGameInstance.h"
#include "LSLevelTypes.h"

void ULSMainMenuWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	PlayButton->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandlePlay);
	LevelSelectButton->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandleLevelSelect);
	ControlsButton->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandleControls);
	QuitButton->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandleQuit);
	Level1Button->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandleLevel1);
	Level2Button->OnClicked.AddDynamic(this, &ULSMainMenuWidget::HandleLevel2);
	LevelSelectBackButton->OnClicked.AddDynamic(this, &ULSMainMenuWidget::ShowMainPanel);
	ControlsPanel->OnClosed.AddDynamic(this, &ULSMainMenuWidget::ShowMainPanel);
}

void ULSMainMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		TotalPetalsText->SetText(FText::FromString(FString::Printf(TEXT("Golden Petals: %d"), GameInstance->GetTotalPetals())));
	}

	Level1BestText->SetText(MakeBestText(Level1));
	Level2BestText->SetText(IsLevel1Finished() ? MakeBestText(Level2) : NSLOCTEXT("LastSeed", "LevelLocked", "Locked: finish Level 1"));
	Level2Button->SetIsEnabled(IsLevel1Finished());

	ShowMainPanel();
}

bool ULSMainMenuWidget::IsLevel1Finished() const
{
	const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>();
	return GameInstance && GameInstance->IsLevelFinished(FName(Level1.GetAssetName()));
}

FText ULSMainMenuWidget::MakeBestText(const TSoftObjectPtr<UWorld>& Level) const
{
	const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>();
	const FName LevelName(Level.GetAssetName());
	if (!GameInstance || !GameInstance->IsLevelFinished(LevelName))
	{
		return NSLOCTEXT("LastSeed", "LevelNotFinished", "Not finished yet");
	}

	const FLSLevelRecord Record = GameInstance->GetLevelRecord(LevelName);
	return FText::FromString(FString::Printf(TEXT("Best: %d stars, %s, %d petals"),
		Record.BestStars, *LSFormatTime(Record.BestTimeSeconds).ToString(), Record.BestPetals));
}

void ULSMainMenuWidget::ShowMainPanel()
{
	LevelSelectPanel->SetVisibility(ESlateVisibility::Collapsed);
	ControlsPanel->SetVisibility(ESlateVisibility::Collapsed);
	MainPanel->SetVisibility(ESlateVisibility::Visible);
	PlayButton->SetFocus();
}

void ULSMainMenuWidget::HandlePlay()
{
	// Play goes to the furthest unlocked level. Level Select is how to replay an earlier one.
	UGameplayStatics::OpenLevelBySoftObjectPtr(this, IsLevel1Finished() ? Level2 : Level1);
}

void ULSMainMenuWidget::HandleLevelSelect()
{
	MainPanel->SetVisibility(ESlateVisibility::Collapsed);
	LevelSelectPanel->SetVisibility(ESlateVisibility::Visible);
	Level1Button->SetFocus();
}

void ULSMainMenuWidget::HandleControls()
{
	MainPanel->SetVisibility(ESlateVisibility::Collapsed);
	ControlsPanel->Open();
}

void ULSMainMenuWidget::HandleQuit()
{
	UKismetSystemLibrary::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false);
}

void ULSMainMenuWidget::HandleLevel1()
{
	UGameplayStatics::OpenLevelBySoftObjectPtr(this, Level1);
}

void ULSMainMenuWidget::HandleLevel2()
{
	UGameplayStatics::OpenLevelBySoftObjectPtr(this, Level2);
}
