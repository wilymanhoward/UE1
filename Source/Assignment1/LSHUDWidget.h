// Last Seed - the in-game display.
//
// Purpose: shows the form icon and name, Life Notes, Golden Petals, the timer, the restoration bar and prompt text
// that fades away. The layout is built in a Blueprint child, and these names must match its widgets exactly.
// Design pattern: observer. Forms, notes and restoration update from events. The timer and petals are read each frame.
// Connections: created by ALSPlayerController. Listens to ASeedBall and URestorationSubsystem. Reads ALSGameMode.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "SeedFormTypes.h"
#include "LSHUDWidget.generated.h"

class ASeedBall;
class UImage;
class UProgressBar;
class UTextBlock;
class UTexture2D;

UCLASS(Abstract)
class ASSIGNMENT1_API ULSHUDWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Connects the form display to the ball. */
	void SetBall(ASeedBall* Ball);

	/** Shows Message for Duration seconds, then fades it out. */
	void ShowPrompt(const FText& Message, float Duration);

protected:
	virtual void NativeConstruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

	/** Icon of the active form. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UImage> FormIcon;

	/** Name of the active form. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> FormNameText;

	/** Life Notes collected and total. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> NotesText;

	/** Golden Petals collected. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> PetalsText;

	/** Level time. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> TimerText;

	/** How restored the world is. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UProgressBar> RestorationBar;

	/** Tutorial and prompt messages. Fades out by itself. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> PromptText;

	/** The icon for each form. A form with no entry keeps the current icon. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD")
	TMap<ESeedForm, TObjectPtr<UTexture2D>> FormIcons;

	/** Seconds a prompt takes to fade out after its duration ends. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.01"))
	float PromptFadeTime = 0.5f;

private:
	UFUNCTION()
	void HandleFormChanged(ESeedForm OldForm, ESeedForm NewForm);

	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	UFUNCTION()
	void HandleRestorationChanged(float Restoration);

	void ShowForm(ESeedForm Form);
	void RefreshNotes();

	float PromptTimeRemaining = 0.f;
};
