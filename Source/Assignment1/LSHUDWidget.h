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
	void ShowHint(const FText& Title, const FText& Keys, const FText& Message, float Duration);

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

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UWidget> PromptPanel;
	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UTextBlock> PromptTitleText;
	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UTextBlock> PromptKeyText;
	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UWidget> NoticePanel;
	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UTextBlock> NoticeText;

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
	float NoticeTimeRemaining = 0.f;

	// Emberwood counts its notes as energy (ALevelGoal::bEnergyFinale).
	bool bCountsEnergy = false;

	// --- Emberwood's energy bar: a breathing glow, a flickering tip and drifting sparks, all brighter after a pickup ---

	/** Adds the glow, tip and spark images beside the bar, in the bar's own canvas. */
	void BuildEnergyEffects();
	void TickEnergyEffects(float DeltaSeconds);
	void SpawnEnergySpark(float FillWidth);

	UPROPERTY(Transient)
	TObjectPtr<UImage> EnergyGlow;

	UPROPERTY(Transient)
	TObjectPtr<UImage> EnergyTip;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UImage>> EnergySparks;

	TArray<FVector2D> SparkVelocities;
	TArray<float> SparkAges;
	TArray<float> SparkLifetimes;

	/** The bar's left end and vertical centre, in its canvas slot's offset space. */
	FVector2D BarOrigin = FVector2D::ZeroVector;
	float BarWidth = 0.f;

	/** 1 right after an energy pickup, easing back to 0. */
	float EnergyPulse = 0.f;
	float SparkCountdown = 0.f;
	float EnergyTime = 0.f;
};
