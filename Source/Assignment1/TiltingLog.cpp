// See TiltingLog.h for this class's purpose, pattern and connections.

#include "TiltingLog.h"

#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"

ATiltingLog::ATiltingLog()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Beam = CreateDefaultSubobject<USceneComponent>(TEXT("Beam"));
	Beam->SetupAttachment(Root);
	Beam->SetMobility(EComponentMobility::Movable);

	Deck = CreateDefaultSubobject<UBoxComponent>(TEXT("Deck"));
	Deck->SetupAttachment(Beam);
	Deck->SetMobility(EComponentMobility::Movable);
	Deck->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(Beam);
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	LogMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LogMesh"));
	LogMesh->SetupAttachment(Beam);
	LogMesh->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
}

void ATiltingLog::BeginPlay()
{
	Super::BeginPlay();

	// Sized here, so changing the tuning numbers on a placed log resizes its surface to match.
	Deck->SetBoxExtent(FVector(HalfLength, HalfWidth, 25.f));
	Deck->SetRelativeLocation(FVector(0.f, 0.f, -25.f));
	Trigger->SetBoxExtent(FVector(HalfLength, HalfWidth, 100.f));
	Trigger->SetRelativeLocation(FVector(0.f, 0.f, 100.f));

	// It starts settled on its counterweight, so the first thing the player sees is the way it rests.
	TiltDegrees = CounterweightKgCm > 0.f ? MaxTiltDegrees : 0.f;
	Beam->SetRelativeRotation(FRotator(TiltDegrees, 0.f, 0.f));
}

float ATiltingLog::GetLoadKgCm() const
{
	TArray<UPrimitiveComponent*> Components;
	Trigger->GetOverlappingComponents(Components);

	const FVector Pivot = GetActorLocation();
	const FVector Along = Beam->GetForwardVector();
	float Load = 0.f;
	for (const UPrimitiveComponent* Component : Components)
	{
		if (Component->IsSimulatingPhysics())
		{
			Load += Component->GetMass() * FVector::DotProduct(Component->GetComponentLocation() - Pivot, Along);
		}
	}
	return Load;
}

void ATiltingLog::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Weight on the +X side pushes that end down, which is negative tilt, and the counterweight pushes the other way.
	const float Acceleration = (CounterweightKgCm - GetLoadKgCm()) * TiltResponse;
	TiltSpeed += (Acceleration - TiltSpeed * Damping) * DeltaSeconds;
	TiltDegrees += TiltSpeed * DeltaSeconds;

	if (FMath::Abs(TiltDegrees) >= MaxTiltDegrees)
	{
		// It rests on its stop, so it doesn't bounce the ball when it lands.
		TiltDegrees = FMath::Clamp(TiltDegrees, -MaxTiltDegrees, MaxTiltDegrees);
		TiltSpeed = 0.f;
	}

	Beam->SetRelativeRotation(FRotator(TiltDegrees, 0.f, 0.f));
}
