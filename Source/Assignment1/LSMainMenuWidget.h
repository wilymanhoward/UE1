// Last Seed - the main menu.
//
// Purpose: Play, Level Select, Controls and Quit. Level 2 stays locked until Level 1 has been finished. The layout
// is built in a Blueprint child, and these names must match its widgets exactly.
// Design pattern: none. It forwards button clicks.
// Connections: created by ALSPlayerController in the menu level. Reads records from ULSGameInstance. Holds a ULSControlsWidget.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSMainMenuWidget.generated.h"

class ULSControlsWidget;
class UButton;
class UTextBlock;
class UWidget;
class UWorld;

UCLASS(Abstract)
class ASSIGNMENT1_API ULSMainMenuWidget : public UUserWidget
{
	GENERATED_BODY()

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;

	/** Holds the four main buttons. Hidden while another panel is open. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UWidget> MainPanel;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> PlayButton;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> LevelSelectButton;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> ControlsButton;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> QuitButton;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> TotalPetalsText;

	/** Holds the level select widgets below. Set it to Collapsed in the layout. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UWidget> LevelSelectPanel;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> Level1Button;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> Level2Button;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> Level1BestText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> Level2BestText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> LevelSelectBackButton;

	/** A Controls widget placed in the layout. Set it to Collapsed in the layout. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<ULSControlsWidget> ControlsPanel;

	/** The Withered Forest level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Levels")
	TSoftObjectPtr<UWorld> Level1;

	/** The Frozen Peaks level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Levels")
	TSoftObjectPtr<UWorld> Level2;

private:
	UFUNCTION()
	void HandlePlay();

	UFUNCTION()
	void HandleLevelSelect();

	UFUNCTION()
	void HandleControls();

	UFUNCTION()
	void HandleQuit();

	UFUNCTION()
	void HandleLevel1();

	UFUNCTION()
	void HandleLevel2();

	UFUNCTION()
	void ShowMainPanel();

	bool IsLevel1Finished() const;
	FText MakeBestText(const TSoftObjectPtr<UWorld>& Level) const;
};
