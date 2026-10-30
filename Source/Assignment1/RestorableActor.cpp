// See RestorableActor.h for this class's purpose, pattern and connections.

#include "RestorableActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "LSDefaultMeshes.h"
#include "RestorationSubsystem.h"

ARestorableActor::ARestorableActor()
{
	PrimaryActorTick.bCanEverTick = true;
	// Only ticks while growing. A level may hold hundreds of these.
	PrimaryActorTick.bStartWithTickEnabled = false;

#if WITH_EDITORONLY_DATA
	// Keeps it listening in a World Partition level, even when far from the player.
	bIsSpatiallyLoaded = false;
#endif

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Root);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cone());
}

void ARestorableActor::BeginPlay()
{
	Super::BeginPlay();

	FullScale = Mesh->GetRelativeScale3D();
	Mesh->SetVisibility(false);

	URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	Restoration->OnRestorationChanged.AddDynamic(this, &ARestorableActor::HandleRestorationChanged);
	Restoration->OnNoteCollected.AddDynamic(this, &ARestorableActor::HandleNoteCollected);
}

void ARestorableActor::HandleRestorationChanged(float Restoration)
{
	if (Restoration >= RestorationThreshold)
	{
		StartGrowing();
	}
}

void ARestorableActor::HandleNoteCollected(FVector Location)
{
	// Comparing squared distances avoids a square root for every plant on every note.
	if (FVector::DistSquared(Location, GetActorLocation()) <= FMath::Square(NoteRadius))
	{
		StartGrowing();
	}
}

void ARestorableActor::StartGrowing()
{
	if (bGrowing || bGrown)
	{
		return;
	}
	bGrowing = true;

	Mesh->SetRelativeScale3D(FVector::ZeroVector);
	Mesh->SetVisibility(true);
	SetActorTickEnabled(true);
	PlayGrowEffect();
}

void ARestorableActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	GrowElapsed += DeltaSeconds;
	const float Progress = FMath::Min(GrowElapsed / GrowDuration, 1.f);

	// A "back ease out" curve: starts fast, passes 1, then settles back to exactly 1 when Progress is 1.
	const float Remaining = Progress - 1.f;
	const float Eased = 1.f + (BounceAmount + 1.f) * FMath::Pow(Remaining, 3.f) + BounceAmount * FMath::Square(Remaining);
	Mesh->SetRelativeScale3D(FullScale * Eased);

	if (Progress >= 1.f)
	{
		bGrowing = false;
		bGrown = true;
		SetActorTickEnabled(false);
	}
}
