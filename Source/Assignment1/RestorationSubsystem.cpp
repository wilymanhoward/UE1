// See RestorationSubsystem.h for this class's purpose, patterns and connections.

#include "RestorationSubsystem.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "LifeNote.h"
#include "LSGameMode.h"
#include "TimerManager.h"

namespace
{
	// Fixed by the game design, and the music has one stem per milestone, so these aren't tuning values.
	constexpr float MilestoneThresholds[] = { 0.25f, 0.5f, 0.75f, 1.f };
}

bool URestorationSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void URestorationSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	NotesTotal = 0;
	for (TActorIterator<ALifeNote> It(&InWorld); It; ++It)
	{
		++NotesTotal;
	}
	UE_LOG(LogTemp, Log, TEXT("Restoration: found %d Life Notes"), NotesTotal);

	// Home from Emberwood: the forest is already healed. Next tick, once listeners have bound in BeginPlay.
	const ALSGameMode* GameMode = InWorld.GetAuthGameMode<ALSGameMode>();
	if (GameMode && GameMode->IsRestoredArrival())
	{
		InWorld.GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &URestorationSubsystem::RestoreFully));
	}
}

void URestorationSubsystem::RestoreFully()
{
	for (TActorIterator<ALifeNote> It(GetWorld()); It; ++It)
	{
		It->Destroy();
	}
	NotesCollected = NotesTotal;
	SetRestoration(1.f);
	LockInRestoration();
}

float URestorationSubsystem::GetNoteFraction() const
{
	return NotesTotal > 0 ? static_cast<float>(NotesCollected) / NotesTotal : 0.f;
}

void URestorationSubsystem::ReportNoteCollected(const FVector& Location)
{
	++NotesCollected;
	OnNoteCollected.Broadcast(Location);

	// Every note collected always means fully restored, whatever drain happened along the way.
	const bool bAllCollected = NotesTotal > 0 && NotesCollected >= NotesTotal;
	SetRestoration(bAllCollected ? 1.f : FMath::Max(GetNoteFraction() - DrainPenalty, LockedRestoration));
}

void URestorationSubsystem::DrainRestoration(float Amount)
{
	const float NewRestoration = FMath::Max(Restoration - Amount, LockedRestoration);
	// Store the drain as a penalty, so the next note adds to the drained value and doesn't undo the drain.
	DrainPenalty = FMath::Max(GetNoteFraction() - NewRestoration, 0.f);
	SetRestoration(NewRestoration);
}

void URestorationSubsystem::LockInRestoration()
{
	LockedRestoration = Restoration;
}

void URestorationSubsystem::SetRestoration(float NewRestoration)
{
	if (FMath::IsNearlyEqual(NewRestoration, Restoration))
	{
		return;
	}

	Restoration = NewRestoration;
	OnRestorationChanged.Broadcast(Restoration);
	BroadcastNewMilestones();
}

void URestorationSubsystem::BroadcastNewMilestones()
{
	// A loop, because in a level with few notes one note can pass more than one milestone.
	while (NextMilestone < UE_ARRAY_COUNT(MilestoneThresholds)
		&& Restoration >= MilestoneThresholds[NextMilestone] - UE_KINDA_SMALL_NUMBER)
	{
		UE_LOG(LogTemp, Log, TEXT("Restoration: milestone %d reached"), NextMilestone);
		OnMilestoneReached.Broadcast(NextMilestone);
		++NextMilestone;
	}
}
