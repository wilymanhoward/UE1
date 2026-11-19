// See CrackedWall.h for this class's purpose and connections.

#include "CrackedWall.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSDefaultMeshes.h"
#include "SeedBall.h"
#include "Sound/SoundBase.h"

ACrackedWall::ACrackedWall()
{
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	Mesh->SetRelativeScale3D(FVector(0.5f, 3.f, 3.f));

	DebrisMesh = LSDefaultMeshes::Cube();
}

void ACrackedWall::OnBallHit(ASeedBall* Ball, FVector ImpactVelocity)
{
	if (bBroken || Ball->GetCurrentForm() != ESeedForm::Stone)
	{
		return;
	}

	if (Ball->IsSlamming() || ImpactVelocity.Size() >= BreakSpeed)
	{
		Break(ImpactVelocity);
	}
}

void ACrackedWall::Break(const FVector& ImpactVelocity)
{
	bBroken = true;

	// Read the bounds and clear the collision before spawning, so debris doesn't start inside a solid wall.
	const FBox WallBounds = Mesh->Bounds.GetBox();
	Mesh->SetVisibility(false);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	for (AActor* Rubble : RubbleActors)
	{
		if (Rubble)
		{
			Rubble->SetActorHiddenInGame(true);
			Rubble->SetActorEnableCollision(false);
		}
	}

	if (DebrisMesh)
	{
		const FVector ImpactDirection = ImpactVelocity.GetSafeNormal();
		for (int32 Index = 0; Index < DebrisCount; ++Index)
		{
			SpawnDebrisChunk(WallBounds, ImpactDirection);
		}
	}

	UGameplayStatics::PlaySoundAtLocation(this, BreakSound, GetActorLocation());
	PlayBreakEffect();
	SetLifeSpan(DebrisLifetime);
}

void ACrackedWall::SpawnDebrisChunk(const FBox& WallBounds, const FVector& ImpactDirection)
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	const FVector Location = FMath::RandPointInBox(WallBounds);
	AStaticMeshActor* Chunk = GetWorld()->SpawnActor<AStaticMeshActor>(Location, FRotator(FMath::VRand().Rotation()), SpawnParams);
	if (!Chunk)
	{
		return;
	}

	// Static mesh actors spawn as Static, and only a Movable component can simulate physics.
	UStaticMeshComponent* ChunkMesh = Chunk->GetStaticMeshComponent();
	ChunkMesh->SetMobility(EComponentMobility::Movable);
	ChunkMesh->SetStaticMesh(DebrisMesh);
	ChunkMesh->SetWorldScale3D(FVector(DebrisScale * FMath::FRandRange(0.45f, 1.45f)));
	ChunkMesh->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
	// Keep the rubble physical against the terrain without stopping the ball or hitting other fragments.
	ChunkMesh->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
	ChunkMesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	ChunkMesh->SetSimulatePhysics(true);
	ChunkMesh->SetMassOverrideInKg(NAME_None, DebrisMassKg, true);

	// Mostly the way the ball was travelling, with a random spread.
	const FVector Forward = ImpactDirection.GetSafeNormal2D();
	const FVector Spread = FMath::VRand() * 0.65f + FVector(0.f, 0.f, 0.75f);
	const FVector LaunchDirection = (Forward + Spread).GetSafeNormal();
	ChunkMesh->AddImpulse(LaunchDirection * DebrisSpeed * FMath::FRandRange(0.45f, 1.15f), NAME_None, true);
	ChunkMesh->SetPhysicsAngularVelocityInDegrees(FMath::VRand() * FMath::FRandRange(90.f, 310.f));

	Chunk->SetLifeSpan(DebrisLifetime);
}
