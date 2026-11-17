// Last Seed - turns player input into commands for the ball.
//
// Purpose: builds every Enhanced Input action and the mapping context in code at runtime, so no input
// assets are needed, and forwards input to the possessed ASeedBall. It also owns every widget, switches between
// game and UI input, plays story sequences and cards, and applies the volume settings.
// Design pattern: command-style forwarding. The controller knows the keys, the ball knows the behaviour.
// Connections: spawned by ALSGameMode. Calls the input functions on ASeedBall. Creates ULSHUDWidget,
// ULSMainMenuWidget, ULSPauseMenuWidget, ULSResultsWidget and ULSStoryCardWidget. Reads ULSGameInstance.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "LSIntroWidget.h"
#include "LSLevelTypes.h"
#include "SeedFormTypes.h"
#include "LSPlayerController.generated.h"

class ALevelSequenceActor;
class ALSGameMode;
class ASeedBall;
class UInputAction;
class UInputMappingContext;
class ULevelSequence;
class ULSHUDWidget;
class ULSMainMenuWidget;
class ULSPauseMenuWidget;
class ULSResultsWidget;
class ULSStoryCardWidget;
class USoundBase;
class USoundClass;
class USoundMix;
class UUserWidget;
class UWorld;
struct FInputActionInstance;
struct FInputActionValue;

UCLASS()
class ASSIGNMENT1_API ALSPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** Shows a message to the player for the given number of seconds. */
	UFUNCTION(BlueprintCallable, Category = "UI")
	void ShowPrompt(const FText& Message, float Duration);

	UFUNCTION(BlueprintCallable, Category = "UI")
	void ShowFormUnlock(ESeedForm Form, const FText& Message, float Duration);

	/**
	 * Plays Sequence if it is set, or otherwise shows Cards, with gameplay input off. OnFinished runs afterward,
	 * and runs straight away if there is nothing to play.
	 */
	void PlayStory(ULevelSequence* Sequence, const TArray<FText>& Cards, TFunction<void()> OnFinished = nullptr);

	/** Plays the painted opening cutscene (ULSIntroWidget) with gameplay input off. Shots must not be empty. */
	void PlayIntro(const TArray<FLSIntroShot>& Shots, USoundBase* Music, USoundBase* VoiceOver);

	/** Opens the results screen. */
	void ShowResults(const FLSLevelResult& Result);

	/** Closes the open menu and returns to the game. */
	void CloseMenu();

	/** The pause menu's Restart button: returns the ball to its last checkpoint. */
	void RestartFromCheckpoint();

	/** Opens the main menu level. */
	void ReturnToMainMenu();

	/** Sends the volumes stored in ULSGameInstance to the sound classes. */
	void ApplyVolumeSettings();

	/** Console test command: drains restoration by Amount (0 to 1), as a Wither Blob does. */
	UFUNCTION(Exec)
	void LSDrainRestoration(float Amount);

	/** Console test command: unlocks Stone and Dandelion. */
	UFUNCTION(Exec)
	void LSUnlockAllForms();

	/** Console test command: deletes the save file so unlock tests can start fresh. */
	UFUNCTION(Exec)
	void LSDeleteSave();

	/** Console test command: kills the ball to test respawning. */
	UFUNCTION(Exec)
	void LSKillBall();

	/** Console test command: completes the level as if the ball had reached the Level Goal, which must be placed. */
	UFUNCTION(Exec)
	void LSCompleteLevel();

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void OnPossess(APawn* InPawn) override;

	/** Turns on F1 (unlock all forms), F2 (teleport to the next checkpoint) and F3 (collect 5 notes). Untick before submitting. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Dev")
	bool bEnableDevCheats = false;

	/** Assign WBP_HUD. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSubclassOf<ULSHUDWidget> HUDClass;

	/** Assign WBP_MainMenu. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSubclassOf<ULSMainMenuWidget> MainMenuClass;

	/** Assign WBP_PauseMenu. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSubclassOf<ULSPauseMenuWidget> PauseMenuClass;

	/** Assign WBP_Results. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSubclassOf<ULSResultsWidget> ResultsClass;

	/** Assign WBP_StoryCard. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSubclassOf<ULSStoryCardWidget> StoryCardClass;

	/** Opened by the pause menu's Main Menu button and after the credits. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
	TSoftObjectPtr<UWorld> MainMenuLevel;

	/** Assign SM_Volume. The sliders do nothing without this and the two sound classes. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Audio")
	TObjectPtr<USoundMix> VolumeMix;

	/** Assign SC_Music. The music slider controls every sound using this class. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Audio")
	TObjectPtr<USoundClass> MusicClass;

	/** Assign SC_SFX. The SFX slider controls every sound using this class. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Audio")
	TObjectPtr<USoundClass> SfxClass;

	/** Multiplies mouse and gamepad look speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float LookSensitivity = 1.f;

	/** Gamepad look speed at full stick. Legacy input scales multiply it by 2.5 to give degrees/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float GamepadLookRate = 60.f;

	/** Stick values below this are ignored, which stops drift on worn sticks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0", ClampMax = "1"))
	float StickDeadZone = 0.2f;

	/** Starting camera pitch in degrees. Negative looks down at the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float InitialCameraPitch = -20.f;

	/** Lowest camera pitch in degrees (looking down from above). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float MinCameraPitch = -70.f;

	/** Highest camera pitch in degrees (looking up from low down). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float MaxCameraPitch = 30.f;

private:
	void OpenMenu(UUserWidget* Menu);
	void SetGameplayInputEnabled(bool bEnabled);
	void SetHUDVisible(bool bVisible);
	/** Turns gameplay input, the HUD and the timer off for a story, replacing any story still playing. */
	void BeginStory(TFunction<void()> OnFinished);
	void FinishStory();
	void AdvanceOpeningTutorial();
	ALSGameMode* GetLSGameMode() const;

	UFUNCTION()
	void HandleStoryCardsFinished();

	UFUNCTION()
	void HandleSequenceFinished();

	void CreateInputObjects();
	void BindInputActions();

	void HandleMove(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleJumpPressed();
	void HandleJumpReleased();
	void HandleSlam();
	void HandleSelectForm(const FInputActionInstance& Instance, ESeedForm Form);
	void HandleCycleForm(const FInputActionValue& Value);
	void HandleTogglePause();
	void HandleDevUnlockForms();
	void HandleDevNextCheckpoint();
	void HandleDevCollectNotes();

	ASeedBall* GetBall() const;

	/** The in-game display. Null in the menu level, or if no HUD Class is assigned. */
	UPROPERTY(Transient)
	TObjectPtr<ULSHUDWidget> HUD;

	/** The menu on screen now, or null during play. */
	UPROPERTY(Transient)
	TObjectPtr<UUserWidget> ActiveMenu;

	/** Plays the current cutscene. Destroyed when it ends. */
	UPROPERTY(Transient)
	TObjectPtr<ALevelSequenceActor> StorySequenceActor;

	TFunction<void()> AfterStory;
	bool bStoryPlaying = false;
	bool bOpeningIntro = false;
	int32 OpeningTutorialStep = 0;
	float TutorialInputTime = 0.f;

	// UPROPERTY keeps these runtime-created objects alive: otherwise garbage collection would delete them.
	/** Maps every key to its action. Created in code. */
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> GameplayContext;

	/** Rolling input. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	/** Camera input. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	/** Jump and glide input. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> JumpAction;

	/** Ground slam input. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SlamAction;

	/** Switches to Seed. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectSeedAction;

	/** Switches to Stone Shell. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectStoneAction;

	/** Switches to Dandelion. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectDandelionAction;

	/** Moves to the next or previous form. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> CycleFormAction;

	/** Opens and closes the pause menu. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> PauseAction;

	/** F1 cheat. Only created when dev cheats are on. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> DevUnlockFormsAction;

	/** F2 cheat. Only created when dev cheats are on. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> DevNextCheckpointAction;

	/** F3 cheat. Only created when dev cheats are on. */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> DevCollectNotesAction;
};
