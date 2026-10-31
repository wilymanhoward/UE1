// Last Seed - the end-of-level screen.
//
// Purpose: shows the stars, time, notes, petals and deaths, and which star conditions were met. The layout is built
// in a Blueprint child, and these names must match its widgets exactly.
// Design pattern: none. It displays one FLSLevelResult and forwards button clicks.
// Connections: created by ALSPlayerController with the result from ALSGameMode. Its buttons call ALSGameMode.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSLevelTypes.h"
#include "LSResultsWidget.generated.h"

class UButton;
class UImage;
class UTextBlock;

UCLASS(Abstract)
class ASSIGNMENT1_API ULSResultsWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Fills in every value on the screen. */
	void ShowResult(const FLSLevelResult& Result);

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UImage> Star1;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UImage> Star2;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UImage> Star3;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> TimeText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> NotesText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> PetalsText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> DeathsText;

	/** The second star's condition: all Life Notes. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> NotesConditionText;

	/** Part of the third star's condition: beating the par time. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> ParConditionText;

	/** Part of the third star's condition: enough Golden Petals. */
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> PetalsConditionText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> NextButton;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> RetryButton;

	/** Tint of a star that was earned. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor EarnedStarColor = FLinearColor(1.f, 0.8f, 0.2f);

	/** Tint of a star that was missed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor MissedStarColor = FLinearColor(0.1f, 0.1f, 0.1f);

private:
	UFUNCTION()
	void HandleNext();

	UFUNCTION()
	void HandleRetry();
};
