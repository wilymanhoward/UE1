// See LifeNote.h for this class's purpose, pattern and connections.

#include "LifeNote.h"

#include "Engine/World.h"
#include "RestorationSubsystem.h"

ALifeNote::ALifeNote()
{
#if WITH_EDITORONLY_DATA
	// World Partition only loads actors near the player, and the note total must include the whole level.
	bIsSpatiallyLoaded = false;
#endif
}

void ALifeNote::OnCollected(ASeedBall* Ball)
{
	GetWorld()->GetSubsystem<URestorationSubsystem>()->ReportNoteCollected(GetActorLocation());
}
