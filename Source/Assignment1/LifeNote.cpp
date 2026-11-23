// See LifeNote.h for this class's purpose, pattern and connections.

#include "LifeNote.h"

#include "Engine/World.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

namespace
{
	const FName EmberwoodEnergyTag(TEXT("LS_EmberwoodEnergy"));

	float CollectedFraction(const URestorationSubsystem& Restoration)
	{
		return static_cast<float>(Restoration.GetNotesCollected()) / FMath::Max(1, Restoration.GetNotesTotal());
	}
}

ALifeNote::ALifeNote()
{
#if WITH_EDITORONLY_DATA
	// World Partition only loads actors near the player, and the note total must include the whole level.
	bIsSpatiallyLoaded = false;
#endif
}

void ALifeNote::OnCollected(ASeedBall* Ball)
{
	URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	Restoration->ReportNoteCollected(GetActorLocation());
	if (Ball && ActorHasTag(EmberwoodEnergyTag))
	{
		Ball->AbsorbEmberwoodEnergy(CollectedFraction(*Restoration), ArcMeshes, ArcMaterial);
	}
}

float ALifeNote::GetCollectPitch() const
{
	// Major pentatonic over two octaves. Never a wrong note, whatever order the notes are found in.
	static constexpr float Scale[] = { 1.f, 1.125f, 1.25f, 1.5f, 1.6667f, 2.f, 2.25f, 2.5f, 3.f, 3.3333f };
	const URestorationSubsystem& Restoration = *GetWorld()->GetSubsystem<URestorationSubsystem>();
	if (ActorHasTag(EmberwoodEnergyTag))
	{
		return FMath::Lerp(0.94f, 1.17f, CollectedFraction(Restoration));
	}
	const int32 Count = Restoration.GetNotesCollected();
	return Scale[FMath::Max(Count - 1, 0) % UE_ARRAY_COUNT(Scale)];
}
