// Last Seed - the placeable home of a level's music.
//
// Purpose: gives UAdaptiveMusicComponent an actor that always stays loaded. Place one in each level and assign
// that level's stems on its component.
// Design pattern: none. It only holds the component.
// Connections: owns UAdaptiveMusicComponent.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MusicManager.generated.h"

class UAdaptiveMusicComponent;

UCLASS()
class ASSIGNMENT1_API AMusicManager : public AActor
{
	GENERATED_BODY()

public:
	AMusicManager();

protected:
	/** Click this in the Details panel to assign the stems and the finale track. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UAdaptiveMusicComponent> AdaptiveMusic;
};
