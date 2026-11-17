// See LSPauseMenuWidget.h for this class's purpose and connections.

#include "LSPauseMenuWidget.h"

#include "Components/Button.h"
#include "Components/Slider.h"
#include "Components/TextBlock.h"
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

void ULSPauseMenuWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	for (UButton* Button : {ResumeButton.Get(), RestartButton.Get(), ControlsButton.Get(), MainMenuButton.Get()})
	{
		const bool bSelected = Button->IsHovered() || Button->HasKeyboardFocus() || Button->HasUserFocus(GetOwningPlayer());
		if (UTextBlock* Label = Cast<UTextBlock>(Button->GetContent()))
			Label->SetColorAndOpacity(FSlateColor(bSelected ? FLinearColor(1.f, 0.82f, 0.36f) : FLinearColor(0.92f, 0.91f, 0.84f)));
		Button->SetBackgroundColor(FLinearColor(1.f, 1.f, 1.f, bSelected ? 1.f : 0.f));
	}
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
