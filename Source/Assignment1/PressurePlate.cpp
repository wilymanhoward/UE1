// See PressurePlate.h for this class's purpose, pattern and connections.

#include "PressurePlate.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "LSDefaultMeshes.h"
#include "LSPlayerController.h"
#include "SeedBall.h"

APressurePlate::APressurePlate()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Root);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	Mesh->SetRelativeScale3D(FVector(2.f, 2.f, 0.2f));

	// Slightly narrower than the plate, so a ball resting beside it doesn't count.
	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(Root);
	Trigger->SetBoxExtent(FVector(90.f, 90.f, 50.f));
	Trigger->SetRelativeLocation(FVector(0.f, 0.f, 50.f));
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	TooLightMessage = NSLOCTEXT("LastSeed", "PlateTooLight", "Too light!");
}

void APressurePlate::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Checked every frame, not on overlap events: the ball's mass changes if it switches form on the plate.
	const bool bNowPressed = GetMassOnPlate() >= RequiredMassKg;
	if (bNowPressed != bPressed)
	{
		bPressed = bNowPressed;
		if (bPressed)
		{
			OnPlatePressed.Broadcast();
		}
		else
		{
			OnPlateReleased.Broadcast();
		}
	}

	CurrentDepth = FMath::FInterpConstantTo(CurrentDepth, bPressed ? PressDepth : 0.f, DeltaSeconds, PressSpeed);
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, -CurrentDepth));
}

float APressurePlate::GetMassOnPlate() const
{
	TArray<UPrimitiveComponent*> Components;
	Trigger->GetOverlappingComponents(Components);

	float TotalMass = 0.f;
	for (const UPrimitiveComponent* Component : Components)
	{
		if (Component->IsSimulatingPhysics())
		{
			TotalMass += Component->GetMass();
		}
	}
	return TotalMass;
}

void APressurePlate::OnBallOverlap(ASeedBall* Ball)
{
	const double Now = GetWorld()->GetTimeSeconds();
	if (GetMassOnPlate() >= RequiredMassKg || Now < NextPromptTime)
	{
		return;
	}
	NextPromptTime = Now + PromptCooldown;

	if (ALSPlayerController* PlayerController = Ball->GetController<ALSPlayerController>())
	{
		PlayerController->ShowPrompt(TooLightMessage, PromptDuration);
	}
}
