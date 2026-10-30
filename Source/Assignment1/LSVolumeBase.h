// Last Seed - an invisible box that reacts when the ball enters it.
//
// Purpose: gives every volume in the game the same box setup, so children only write their reaction.
// Design pattern: inheritance for shared setup. Children override OnBallOverlap from ILSInteractable.
// Connections: touched by ASeedBall through ILSInteractable. Children are AKillVolume, ATutorialTrigger,
// AWindVolume, AWaterVolume, AHazardVolume and AThinIce.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "LSVolumeBase.generated.h"

class UBoxComponent;

UCLASS(Abstract)
class ASSIGNMENT1_API ALSVolumeBase : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ALSVolumeBase();

protected:
	/** The living ball inside the box, or null. For children that act every frame while the ball stays inside. */
	ASeedBall* GetBallInside() const;

	/** The trigger area. Resize it with Box Extent, or scale the actor in the level. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UBoxComponent> Box;
};
