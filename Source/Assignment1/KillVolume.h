// Last Seed - a fall-off zone that sends the ball back to its checkpoint.
//
// Purpose: place below gaps and ledges. Any ball entering it dies and respawns.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. Calls ASeedBall::Die.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "KillVolume.generated.h"

UCLASS()
class ASSIGNMENT1_API AKillVolume : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	virtual void OnBallOverlap(ASeedBall* Ball) override;
};
