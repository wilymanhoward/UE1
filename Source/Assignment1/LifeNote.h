// Last Seed - the main collectible.
//
// Purpose: collecting Life Notes restores the world. Phase 4 connects this to URestorationSubsystem.
// Design pattern: template method (implements the OnCollected step of ALSPickupBase).
// Connections: collected by ASeedBall through ALSPickupBase. Counted and reported to the restoration subsystem in Phase 4.

#pragma once

#include "CoreMinimal.h"
#include "LSPickupBase.h"
#include "LifeNote.generated.h"

UCLASS()
class ASSIGNMENT1_API ALifeNote : public ALSPickupBase
{
	GENERATED_BODY()

protected:
	virtual void OnCollected(ASeedBall* Ball) override;
};
