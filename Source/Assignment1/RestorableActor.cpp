// See RestorableActor.h for this class's purpose, pattern and connections.

#include "RestorableActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
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

	WitheredMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WitheredMesh"));
	WitheredMesh->SetupAttachment(Root);
	WitheredMesh->SetMobility(EComponentMobility::Movable);
	WitheredMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ARestorableActor::BeginPlay()
{
	Super::BeginPlay();

	FullScale = Mesh->GetRelativeScale3D();
	WitheredScale = WitheredMesh->GetRelativeScale3D();
	Mesh->SetVisibility(false);

	URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	Restoration->OnRestorationChanged.AddDynamic(this, &ARestorableActor::HandleRestorationChanged);
	Restoration->OnNoteCollected.AddDynamic(this, &ARestorableActor::HandleNoteCollected);
	if (bStartGrown)
	{
		bGrown = true;
		Mesh->SetVisibility(true);
		WitheredMesh->SetVisibility(false);
	}
}

void ARestorableActor::SetCursed(bool bValue)
{
	if (bCursed == bValue) return;
	bCursed = bValue;
	if (bValue)
	{
		bRestoreAfterCurse = bGrown || bGrowing;
		CurseScale = Mesh->GetRelativeScale3D();
		bGrowing = false;
		bGrown = false;
		GrowElapsed = 0.f;
		SetActorTickEnabled(true);
	}
	else
	{
		Mesh->SetVisibility(bRestoreAfterCurse);
		Mesh->SetRelativeScale3D(FullScale);
		WitheredMesh->SetVisibility(!bRestoreAfterCurse);
		WitheredMesh->SetRelativeScale3D(WitheredScale);
		bGrown = bRestoreAfterCurse;
		bGrowthBegun = false;
		SetActorTickEnabled(false);
	}
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
	if (bCursed || bGrowing || bGrown)
	{
		return;
	}
	bGrowing = true;

	GrowElapsed = -FMath::FRandRange(0.f, MaxStartDelay);
	ShakePhase = FMath::FRandRange(0.f, 2.f * PI);
	SetActorTickEnabled(true);
	if (GrowElapsed >= 0.f)
	{
		BeginGrowth();
	}
}

void ARestorableActor::BeginGrowth()
{
	bGrowthBegun = true;
	Mesh->SetRelativeScale3D(FVector::ZeroVector);
	Mesh->SetVisibility(true);

	// When many grow at once, only every few tenths of a second gets a sound, so a stand of trees layers into one
	// swell rather than a wall of noise. Shared by every restorable in the game.
	static double LastSoundTime = -1.0;
	const double Now = GetWorld()->GetTimeSeconds();
	if (GrowSound && (Now - LastSoundTime > 0.35 || Now < LastSoundTime))
	{
		LastSoundTime = Now;
		UGameplayStatics::PlaySoundAtLocation(this, GrowSound, GetActorLocation(), FMath::FRandRange(0.8f, 1.f), FMath::FRandRange(0.9f, 1.1f));
	}
	PlayGrowEffect();
}

void ARestorableActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bCursed)
	{
		GrowElapsed += DeltaSeconds;
		const float Fade = FMath::SmoothStep(0.f, 0.65f, GrowElapsed);
		Mesh->SetRelativeScale3D(CurseScale * (1.f - Fade));
		WitheredMesh->SetVisibility(true);
		WitheredMesh->SetRelativeScale3D(WitheredScale * Fade);
		if (Fade >= 1.f) { Mesh->SetVisibility(false); SetActorTickEnabled(false); }
		return;
	}

	GrowElapsed += DeltaSeconds;
	if (GrowElapsed < 0.f)
	{
		return;
	}
	if (!bGrowthBegun)
	{
		BeginGrowth();
	}
	const float Progress = FMath::Min(GrowElapsed / GrowDuration, 1.f);

	// A "back ease out" curve: starts fast, passes 1, then settles back to exactly 1 when Progress is 1.
	const float Remaining = Progress - 1.f;
	const float Eased = 1.f + (BounceAmount + 1.f) * FMath::Pow(Remaining, 3.f) + BounceAmount * FMath::Square(Remaining);
	Mesh->SetRelativeScale3D(FullScale * Eased);
	// The dead form is gone by the time the new growth passes half its size.
	WitheredMesh->SetRelativeScale3D(WitheredScale * FMath::Max(1.f - Progress * 2.f, 0.f));

	// Trembles as it pushes up, two sways out of step so it rocks rather than ticks, dying away as it settles.
	const float Fade = FMath::Pow(1.f - Progress, 1.5f);
	const float Time = 2.f * PI * ShakeFrequency * GrowElapsed;
	const FRotator Shake(ShakeDegrees * Fade * FMath::Sin(Time + ShakePhase), 0.f, ShakeDegrees * 0.7f * Fade * FMath::Sin(Time * 1.37f + ShakePhase * 2.f));
	Mesh->SetRelativeRotation(Shake);
	WitheredMesh->SetRelativeRotation(Shake * 1.5f);

	if (Progress >= 1.f)
	{
		bGrowing = false;
		bGrown = true;
		Mesh->SetRelativeRotation(FRotator::ZeroRotator);
		WitheredMesh->SetVisibility(false);
		SetActorTickEnabled(false);
	}
}
