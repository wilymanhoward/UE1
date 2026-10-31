// Last Seed - the controls list.
//
// Purpose: lists every control. It is placed inside the main menu and pause menu layouts, so both show the same list.
// Design pattern: observer. OnClosed tells whichever menu holds it that the player pressed Back.
// Connections: held by ULSMainMenuWidget and ULSPauseMenuWidget.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSControlsWidget.generated.h"

class UButton;
class UTextBlock;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnControlsClosed);

UCLASS(Abstract)
class ASSIGNMENT1_API ULSControlsWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Makes the list visible and focuses its Back button. */
	void Open();

	/** Fires when the player presses Back. */
	UPROPERTY(BlueprintAssignable, Category = "Controls")
	FOnControlsClosed OnClosed;

protected:
	virtual void NativeOnInitialized() override;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> ControlsText;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UButton> BackButton;

private:
	UFUNCTION()
	void HandleBack();
};
