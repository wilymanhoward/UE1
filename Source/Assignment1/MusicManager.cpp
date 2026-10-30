// See MusicManager.h for this class's purpose and connections.

#include "MusicManager.h"

#include "AdaptiveMusicComponent.h"
#include "Components/SceneComponent.h"

AMusicManager::AMusicManager()
{
#if WITH_EDITORONLY_DATA
	// World Partition must not unload the music when the player moves away from this actor.
	bIsSpatiallyLoaded = false;
#endif

	// A root gives the actor a position, which an actor needs in order to be placed in a level.
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));

	AdaptiveMusic = CreateDefaultSubobject<UAdaptiveMusicComponent>(TEXT("AdaptiveMusic"));
}
