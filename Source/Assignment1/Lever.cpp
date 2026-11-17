// See Lever.h for this class's purpose, pattern and connections.

#include "Lever.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "GameFramework/Pawn.h"

ALever::ALever()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Base = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Base"));
	Base->SetupAttachment(Root);
	Base->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

	Iron = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Iron"));
	Iron->SetupAttachment(Root);
	Iron->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

	Cap = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cap"));
	Cap->SetupAttachment(Root);
	Cap->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	ArmPivot = CreateDefaultSubobject<USceneComponent>(TEXT("ArmPivot"));
	ArmPivot->SetupAttachment(Root);
	ArmPivot->SetMobility(EComponentMobility::Movable);
	ArmPivot->SetRelativeLocation(FVector(0.f, 0.f, 46.f));

	Rod = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Rod"));
	Rod->SetupAttachment(ArmPivot);
	Rod->SetMobility(EComponentMobility::Movable);
	Rod->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Grip = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Grip"));
	Grip->SetupAttachment(ArmPivot);
	Grip->SetMobility(EComponentMobility::Movable);
	Grip->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	PushZone = CreateDefaultSubobject<UBoxComponent>(TEXT("PushZone"));
	PushZone->SetupAttachment(Root);
	PushZone->SetBoxExtent(FVector(75.f, 70.f, 60.f));
	PushZone->SetRelativeLocation(FVector(-185.f, 0.f, 70.f));
	PushZone->SetCollisionProfileName(TEXT("Trigger"));
}

void ALever::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Checked every frame rather than on overlap events, so a block that slides away releases it straight away.
	const bool bNowOn = GetMassAgainst() >= RequiredMassKg;
	if (bNowOn != bOn)
	{
		bOn = bNowOn;
		if (bOn)
		{
			OnLeverOn.Broadcast();
		}
		else
		{
			OnLeverOff.Broadcast();
		}
	}

	CurrentPitch = FMath::FInterpConstantTo(CurrentPitch, bOn ? OnPitch : OffPitch, DeltaSeconds, SwingSpeed);
	ArmPivot->SetRelativeRotation(FRotator(CurrentPitch, 0.f, 0.f));
}

float ALever::GetMassAgainst() const
{
	TArray<UPrimitiveComponent*> Components;
	PushZone->GetOverlappingComponents(Components);

	float TotalMass = 0.f;
	for (const UPrimitiveComponent* Component : Components)
	{
		// The player's ball doesn't count: the lever is held by something pushed against it, not by sitting there.
		if (Component->IsSimulatingPhysics() && !Cast<APawn>(Component->GetOwner()))
		{
			TotalMass += Component->GetMass();
		}
	}
	return TotalMass;
}
