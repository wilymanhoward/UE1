// See PushableBlock.h for this class's purpose and connections.

#include "PushableBlock.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "LSDefaultMeshes.h"

APushableBlock::APushableBlock()
{
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	Mesh->SetSimulatePhysics(true);
	// Pressure plates only see bodies that generate overlap events.
	Mesh->SetGenerateOverlapEvents(true);
	// The ball pushes low on the block, which would tip it over. It should slide instead.
	Mesh->BodyInstance.bLockXRotation = true;
	Mesh->BodyInstance.bLockYRotation = true;
}

void APushableBlock::BeginPlay()
{
	Super::BeginPlay();

	StartTransform = GetActorTransform();
	Mesh->SetMassOverrideInKg(NAME_None, MassKg, true);
}

void APushableBlock::FellOutOfWorld(const UDamageType& DamageType)
{
	// Deliberately skips Super, which would destroy the block.
	SetActorTransform(StartTransform, false, nullptr, ETeleportType::TeleportPhysics);
	Mesh->SetPhysicsLinearVelocity(FVector::ZeroVector);
	Mesh->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
}
