// Last Seed - the pause menu.
//
// Purpose: Resume, Restart from checkpoint, Controls, Music and SFX volume, and Main Menu. The layout is built in a
// Blueprint child, and these names must match its widgets exactly.
// Design pattern: none. It forwards button clicks.
// Connections: created by ALSPlayerController. Writes volumes to ULSGameInstance. Holds a ULSControlsWidget.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSPauseMenuWidget.generated.h"

class ALSPlayerController;
class ULSControlsWidget;
class UButton;
class USlider;
class UWidget;

UCLASS(Abstract)
class ASSIGNMENT1_API ULSPauseMenuWidget : public UUserWidget
{
	GENERATED_BODY()

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;

	/** Holds the buttons and sliders. Hidden while the controls list is open. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UWidget> MainPanel;

	/** Closes the menu and continues. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> ResumeButton;

	/** Returns the ball to its last checkpoint. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> RestartButton;

	/** Opens the controls list. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> ControlsButton;

	/** Leaves the level for the main menu. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> MainMenuButton;

	/** Music volume from 0 to 1. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<USlider> MusicSlider;

	/** Sound effect volume from 0 to 1. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<USlider> SfxSlider;

	/** A Controls widget placed in the layout. Set it to Collapsed in the layout. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<ULSControlsWidget> ControlsPanel;

private:
	UFUNCTION()
	void HandleResume();

	UFUNCTION()
	void HandleRestart();

	UFUNCTION()
	void HandleControls();

	UFUNCTION()
	void HandleControlsClosed();

	UFUNCTION()
	void HandleMainMenu();

	UFUNCTION()
	void HandleMusicChanged(float Value);

	UFUNCTION()
	void HandleSfxChanged(float Value);

	ALSPlayerController* GetLSPlayerController() const;
};
