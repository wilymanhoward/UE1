// See CrumblingPlatform.h for this class's purpose, pattern and connections.

#include "CrumblingPlatform.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "LSDefaultMeshes.h"

ACrumblingPlatform::ACrumblingPlatform()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Root);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	Mesh->SetRelativeScale3D(FVector(3.f, 3.f, 0.3f));
}

void ACrumblingPlatform::BeginPlay()
{
	Super::BeginPlay();
	MeshRestLocation = Mesh->GetRelativeLocation();
}

void ACrumblingPlatform::OnBallHit(ASeedBall* Ball, FVector ImpactVelocity)
{
	if (State == ECrumbleState::Solid)
	{
		SetState(ECrumbleState::Shaking);
		PlayCrumbleEffect();
	}
}

void ACrumblingPlatform::SetState(ECrumbleState NewState)
{
	State = NewState;

	if (State == ECrumbleState::Shaking)
	{
		StateTimeRemaining = ShakeDuration;
	}
	else if (State == ECrumbleState::Waiting)
	{
		StateTimeRemaining = RespawnDelay;
	}
}

void ACrumblingPlatform::SetMeshPresent(bool bPresent)
{
	Mesh->SetVisibility(bPresent);
	Mesh->SetCollisionEnabled(bPresent ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
}

void ACrumblingPlatform::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	FVector2D ShakeOffset = FVector2D::ZeroVector;

	switch (State)
	{
	case ECrumbleState::Solid:
		return;

	case ECrumbleState::Shaking:
		ShakeOffset = FMath::RandPointInCircle(ShakeAmplitude);
		StateTimeRemaining -= DeltaSeconds;
		if (StateTimeRemaining <= 0.f)
		{
			ShakeOffset = FVector2D::ZeroVector;
			SetState(ECrumbleState::Falling);
		}
		break;

	case ECrumbleState::Falling:
		CurrentDrop += FallSpeed * DeltaSeconds;
		if (CurrentDrop >= FallDistance)
		{
			CurrentDrop = FallDistance;
			if (bVanishAfterFall)
			{
				SetMeshPresent(false);
			}
			SetState(ECrumbleState::Waiting);
		}
		break;

	case ECrumbleState::Waiting:
		StateTimeRemaining -= DeltaSeconds;
		if (StateTimeRemaining <= 0.f)
		{
			if (bVanishAfterFall)
			{
				CurrentDrop = 0.f;
				SetMeshPresent(true);
				SetState(ECrumbleState::Solid);
			}
			else
			{
				SetState(ECrumbleState::Returning);
			}
		}
		break;

	case ECrumbleState::Returning:
		CurrentDrop -= ReturnSpeed * DeltaSeconds;
		if (CurrentDrop <= 0.f)
		{
			CurrentDrop = 0.f;
			SetState(ECrumbleState::Solid);
		}
		break;
	}

	Mesh->SetRelativeLocation(MeshRestLocation + FVector(ShakeOffset.X, ShakeOffset.Y, -CurrentDrop));
}
