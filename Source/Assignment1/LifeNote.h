// Last Seed - the main collectible.
//
// Purpose: collecting Life Notes restores the world.
// Design pattern: template method (implements the OnCollected step of ALSPickupBase).
// Connections: collected by ASeedBall through ALSPickupBase. Counted by, and reports to, URestorationSubsystem.

#pragma once

#include "CoreMinimal.h"
#include "LSPickupBase.h"
#include "LifeNote.generated.h"

UCLASS()
class ASSIGNMENT1_API ALifeNote : public ALSPickupBase
{
	GENERATED_BODY()

public:
	ALifeNote();

protected:
	virtual void OnCollected(ASeedBall* Ball) override;

	/** Each note collected chimes one step higher up a pentatonic scale, so collecting them plays a tune. */
	virtual float GetCollectPitch() const override;
};
