// See WindVolume.h for this class's purpose, pattern and connections.

#include "WindVolume.h"

#include "Components/ArrowComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/RotationMatrix.h"
#include "NiagaraComponent.h"
#include "PressurePlate.h"
#include "SeedBall.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 UpdraftWispCount = 8;
	constexpr int32 UpdraftLeafCount = 14;
}

AWindVolume::AWindVolume()
{
	PrimaryActorTick.bCanEverTick = true;

	Particles = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Particles"));
	Particles->SetupAttachment(Box);
	// Tick turns it on once the wind is confirmed to be blowing.
	Particles->SetAutoActivate(false);

	WindAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("WindAudio"));
	WindAudio->SetupAttachment(Box);
	WindAudio->SetAutoActivate(false);

	DirectionArrow = CreateDefaultSubobject<UArrowComponent>(TEXT("DirectionArrow"));
	DirectionArrow->SetupAttachment(Box);
	DirectionArrow->ArrowSize = 4.f;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(
		TEXT("/Game/LastSeed/Materials/M_LS_TrailCrosswind.M_LS_TrailCrosswind"));
	UpdraftPlane = Plane.Object;
	UpdraftMaterial = Material.Object;
}

void AWindVolume::BeginPlay()
{
	Super::BeginPlay();
	if (WindDirection.GetSafeNormal().Z < 0.95f || Particles->GetAsset() || !UpdraftPlane || !UpdraftMaterial)
	{
		return;
	}

	UMaterialInstanceDynamic* Leaf = UMaterialInstanceDynamic::Create(UpdraftMaterial, this);
	Leaf->SetScalarParameterValue(TEXT("Leaf"), 1.f);
	for (int32 Index = 0; Index < UpdraftWispCount + UpdraftLeafCount; ++Index)
	{
		UStaticMeshComponent* Shape = NewObject<UStaticMeshComponent>(this);
		Shape->SetupAttachment(Box);
		Shape->SetMobility(EComponentMobility::Movable);
		Shape->SetUsingAbsoluteScale(true);
		Shape->SetStaticMesh(UpdraftPlane);
		Shape->SetMaterial(0, Index < UpdraftWispCount ? UpdraftMaterial.Get() : Leaf);
		Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Shape->SetGenerateOverlapEvents(false);
		Shape->SetCastShadow(false);
		Shape->SetCullDistance(10500.f);
		Shape->SetVisibility(false);
		Shape->RegisterComponent();
		UpdraftShapes.Add(Shape);
	}
}

void AWindVolume::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// The arrow is editor-only, so it doesn't exist in a packaged game.
	if (DirectionArrow)
	{
		DirectionArrow->SetWorldRotation(WindDirection.Rotation());
	}
}

bool AWindVolume::IsWindActive() const
{
	if (PowerPlate && !PowerPlate->IsPressed())
	{
		return false;
	}
	if (!bPulsing)
	{
		return true;
	}

	// Where we are in the on-then-off cycle. Using world time means no timer state to keep.
	const float CycleTime = FMath::Fmod(GetWorld()->GetTimeSeconds() + PulseOffset, PulseOnTime + PulseOffTime);
	return CycleTime < PulseOnTime;
}

void AWindVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const bool bActive = IsWindActive();
	if (bActive != bWasActive)
	{
		bWasActive = bActive;
		if (bActive)
		{
			Particles->Activate(true);
			WindAudio->FadeIn(SoundFadeTime);
		}
		else
		{
			Particles->Deactivate();
			WindAudio->FadeOut(SoundFadeTime, 0.f);
		}
		PlayWindActiveEffect(bActive);
	}
	if (!UpdraftShapes.IsEmpty())
	{
		UpdateUpdraftVisuals(bActive);
	}

	if (!bActive)
	{
		return;
	}

	if (ASeedBall* Ball = GetBallInside())
	{
		const float Acceleration = Strength * Ball->GetCurrentFormData().WindResponse;
		Ball->AddExternalAcceleration(WindDirection.GetSafeNormal() * Acceleration);
	}
}

void AWindVolume::UpdateUpdraftVisuals(bool bActive)
{
	const float Time = GetWorld()->GetTimeSeconds();
	const FVector Extent = Box->GetUnscaledBoxExtent();
	const FTransform VolumeTransform = Box->GetComponentTransform();
	for (int32 Index = 0; Index < UpdraftShapes.Num(); ++Index)
	{
		UStaticMeshComponent* Shape = UpdraftShapes[Index];
		Shape->SetVisibility(bActive);
		if (!bActive)
		{
			continue;
		}

		const bool bLeaf = Index >= UpdraftWispCount;
		const float Rise = FMath::Frac(Time * (0.36f + (Index % 4) * 0.035f) + Index * 0.618f);
		const float Angle = Index * 2.40f + Rise * 3.8f;
		float Sine, Cosine;
		FMath::SinCos(&Sine, &Cosine, Angle);
		const float Radius = (bLeaf ? 0.72f : 0.55f) * (0.85f + Rise * 0.15f);
		const FVector Local(Extent.X * Radius * Cosine, Extent.Y * Radius * Sine,
			Extent.Z * FMath::Lerp(-0.88f, 0.90f, Rise));
		const float Fade = FMath::SmoothStep(0.f, 0.14f, Rise) * (1.f - FMath::SmoothStep(0.78f, 1.f, Rise));
		const FRotator Rotation = bLeaf ? FRotator(Rise * 260.f, Index * 41.f + Rise * 170.f, 30.f + Index * 53.f)
			: FRotationMatrix::MakeFromXY(FVector(0.13f * Sine, 0.10f * Cosine, 1.f), FVector(-Sine, Cosine, 0.f)).Rotator();
		Shape->SetWorldLocationAndRotation(VolumeTransform.TransformPosition(Local), Rotation);
		Shape->SetWorldScale3D(bLeaf ? FVector(0.38f * Fade, 0.23f * Fade, 1.f)
			: FVector(4.1f * Fade, 1.12f * Fade, 1.f));
	}
}
