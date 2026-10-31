// Last Seed - story text cards.
//
// Purpose: shows story text one card at a time, moving on when the player presses Next. The layout is built in a
// Blueprint child, and these names must match its widgets exactly.
// Design pattern: observer. OnFinished tells the controller the last card is done.
// Connections: created by ALSPlayerController::PlayStory.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSStoryCardWidget.generated.h"

class UButton;
class UTextBlock;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnStoryCardsFinished);

UCLASS(Abstract)
class ASSIGNMENT1_API ULSStoryCardWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Sets the cards and shows the first one. Cards must not be empty. */
	void ShowCards(const TArray<FText>& InCards);

	/** Fires after the last card. */
	UPROPERTY(BlueprintAssignable, Category = "Story")
	FOnStoryCardsFinished OnFinished;

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> CardText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> NextButton;

private:
	UFUNCTION()
	void HandleNext();

	TArray<FText> Cards;
	int32 CardIndex = 0;
};
