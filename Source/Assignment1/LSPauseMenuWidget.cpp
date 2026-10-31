// See LSPauseMenuWidget.h for this class's purpose and connections.

#include "LSPauseMenuWidget.h"

#include "Components/Button.h"
#include "Components/Slider.h"
#include "LSControlsWidget.h"
#include "LSGameInstance.h"
#include "LSPlayerController.h"

void ULSPauseMenuWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	ResumeButton->OnClicked.AddDynamic(this, &ULSPauseMenuWidget::HandleResume);
	RestartButton->OnClicked.AddDynamic(this, &ULSPauseMenuWidget::HandleRestart);
	ControlsButton->OnClicked.AddDynamic(this, &ULSPauseMenuWidget::HandleControls);
	MainMenuButton->OnClicked.AddDynamic(this, &ULSPauseMenuWidget::HandleMainMenu);
	MusicSlider->OnValueChanged.AddDynamic(this, &ULSPauseMenuWidget::HandleMusicChanged);
	SfxSlider->OnValueChanged.AddDynamic(this, &ULSPauseMenuWidget::HandleSfxChanged);
	ControlsPanel->OnClosed.AddDynamic(this, &ULSPauseMenuWidget::HandleControlsClosed);
}

void ULSPauseMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		MusicSlider->SetValue(GameInstance->GetMusicVolume());
		SfxSlider->SetValue(GameInstance->GetSfxVolume());
	}
	ResumeButton->SetFocus();
}

void ULSPauseMenuWidget::NativeDestruct()
{
	// Saved when the menu closes, not on every slider change, because dragging would write to disk many times a second.
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->SaveProgress();
	}

	Super::NativeDestruct();
}

ALSPlayerController* ULSPauseMenuWidget::GetLSPlayerController() const
{
	return GetOwningPlayer<ALSPlayerController>();
}

void ULSPauseMenuWidget::HandleResume()
{
	GetLSPlayerController()->CloseMenu();
}

void ULSPauseMenuWidget::HandleRestart()
{
	GetLSPlayerController()->RestartFromCheckpoint();
}

void ULSPauseMenuWidget::HandleControls()
{
	MainPanel->SetVisibility(ESlateVisibility::Collapsed);
	ControlsPanel->Open();
}

void ULSPauseMenuWidget::HandleControlsClosed()
{
	MainPanel->SetVisibility(ESlateVisibility::Visible);
	ResumeButton->SetFocus();
}

void ULSPauseMenuWidget::HandleMainMenu()
{
	GetLSPlayerController()->ReturnToMainMenu();
}

void ULSPauseMenuWidget::HandleMusicChanged(float Value)
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->SetMusicVolume(Value);
		GetLSPlayerController()->ApplyVolumeSettings();
	}
}

void ULSPauseMenuWidget::HandleSfxChanged(float Value)
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->SetSfxVolume(Value);
		GetLSPlayerController()->ApplyVolumeSettings();
	}
}
