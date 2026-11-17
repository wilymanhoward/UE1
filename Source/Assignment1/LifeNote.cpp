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

float ALifeNote::GetCollectPitch() const
{
	// Major pentatonic over two octaves. Never a wrong note, whatever order the notes are found in.
	static constexpr float Scale[] = { 1.f, 1.125f, 1.25f, 1.5f, 1.6667f, 2.f, 2.25f, 2.5f, 3.f, 3.3333f };
	const int32 Count = GetWorld()->GetSubsystem<URestorationSubsystem>()->GetNotesCollected();
	return Scale[FMath::Max(Count - 1, 0) % UE_ARRAY_COUNT(Scale)];
}
