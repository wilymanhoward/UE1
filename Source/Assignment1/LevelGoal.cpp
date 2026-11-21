// See LevelGoal.h for this class's purpose and connections.

#include "LevelGoal.h"

#include "Engine/World.h"
#include "LevelSequence.h"
#include "LSGameMode.h"
#include "SeedBall.h"

ALevelGoal::ALevelGoal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
#if WITH_EDITORONLY_DATA
	// World Partition must keep this loaded, because the test command looks for it from anywhere in the level.
	bIsSpatiallyLoaded = false;
#endif
}

void ALevelGoal::BeginPlay()
{
	Super::BeginPlay();
	SetActorTickEnabled(bRequireJump);
}

void ALevelGoal::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	OnBallOverlap(GetBallInside());
}

void ALevelGoal::OnBallOverlap(ASeedBall* Ball)
{
	if (!IsValid(Ball) || Ball->IsDead() || (bRequireJump && (!Ball->IsInJump() || Ball->GetVelocity().Z < 80.f)))
	{
		return;
	}
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		SetActorTickEnabled(false);
		GameMode->CompleteLevel(this);
	}
}
