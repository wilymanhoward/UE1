// Last Seed - the line that wakes the storm.
//
// Purpose: starts the assigned storm when the ball enters. Scale it across the start of the climb.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. Calls AWitheringStorm::StartRising.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "StormTrigger.generated.h"

class AWitheringStorm;

UCLASS()
class ASSIGNMENT1_API AStormTrigger : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	virtual void OnBallOverlap(ASeedBall* Ball) override;

protected:
	/** The storm to start. Set this on the placed trigger. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	TObjectPtr<AWitheringStorm> Storm;
};
