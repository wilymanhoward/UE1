// Last Seed - shows a tutorial message the first time the ball enters an area.
//
// Purpose: teaches controls at the moment they are needed. It shows only once, even after a respawn.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. Shows its text through
// ALSPlayerController::ShowPrompt, which the HUD takes over in Phase 7.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "TutorialTrigger.generated.h"

UCLASS()
class ASSIGNMENT1_API ATutorialTrigger : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	virtual void OnBallOverlap(ASeedBall* Ball) override;

protected:
	/** The text to show. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tutorial")
	FText Message;

	/** How long the text stays on screen, in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float DisplayDuration = 5.f;

private:
	bool bShown = false;
};
