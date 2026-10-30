// See LifeNote.h for this class's purpose, pattern and connections.

#include "LifeNote.h"

void ALifeNote::OnCollected(ASeedBall* Ball)
{
	// shortcut: only logs for now, Phase 4 reports to URestorationSubsystem and blooms colour around the note.
	UE_LOG(LogTemp, Log, TEXT("Life Note collected: %s"), *GetName());
}
