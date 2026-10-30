// Last Seed - the contract between the ball and anything it can touch.
//
// Purpose: the ball tells whatever it touched "you were touched", without knowing what that thing is.
// Design pattern: interface / polymorphism. Adding a new world object never requires changing ASeedBall.
// Connections: ASeedBall calls these functions from its overlap and hit events. Pickups, shrines and
// volumes implement them. Both functions default to doing nothing, so a class overrides only what it needs.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "LSInteractable.generated.h"

class ASeedBall;

// Part of the Unreal reflection system. The functions live in ILSInteractable below.
UINTERFACE(MinimalAPI, meta = (CannotImplementInterfaceInBlueprint))
class ULSInteractable : public UInterface
{
	GENERATED_BODY()
};

class ILSInteractable
{
	GENERATED_BODY()

public:
	/** The ball started overlapping this object, such as a pickup or a trigger volume. */
	virtual void OnBallOverlap(ASeedBall* Ball) {}

	/** The ball physically collided with this object. ImpactVelocity is the ball's velocity just before impact. */
	virtual void OnBallHit(ASeedBall* Ball, FVector ImpactVelocity) {}
};
