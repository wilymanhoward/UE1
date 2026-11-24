// See WindVolume.h for this class's purpose, pattern and connections.

#include "WindVolume.h"

#include "Components/ArrowComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "PressurePlate.h"
#include "SeedBall.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 UpdraftRibbonCount = 5;
	constexpr int32 UpdraftLeafCount = 9;
	const FName FlowOpacityParameter(TEXT("FlowOpacity"));
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
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Ribbon(
		TEXT("/Game/LastSeed/Meshes/SM_LS_UpdraftRibbon.SM_LS_UpdraftRibbon"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(
		TEXT("/Game/LastSeed/Materials/M_LS_TrailCrosswind.M_LS_TrailCrosswind"));
	UpdraftPlane = Plane.Object;
	UpdraftRibbon = Ribbon.Object;
	UpdraftMaterial = Material.Object;
}

void AWindVolume::BeginPlay()
{
	Super::BeginPlay();
	if (WindDirection.GetSafeNormal().Z < 0.95f || Particles->GetAsset() || !UpdraftRibbon || !UpdraftPlane || !UpdraftMaterial)
	{
		return;
	}

	UMaterialInstanceDynamic* Leaf = UMaterialInstanceDynamic::Create(UpdraftMaterial, this);
	Leaf->SetScalarParameterValue(TEXT("Leaf"), 1.f);
	for (int32 Index = 0; Index < UpdraftRibbonCount + UpdraftLeafCount; ++Index)
	{
		UStaticMeshComponent* Shape = NewObject<UStaticMeshComponent>(this);
		Shape->SetupAttachment(Box);
		Shape->SetMobility(EComponentMobility::Movable);
		Shape->SetUsingAbsoluteScale(true);
		const bool bRibbon = Index < UpdraftRibbonCount;
		Shape->SetStaticMesh(bRibbon ? UpdraftRibbon.Get() : UpdraftPlane.Get());
		if (bRibbon)
		{
			Shape->CreateDynamicMaterialInstance(0);
		}
		else
		{
			Shape->SetMaterial(0, Leaf);
		}
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
	const FVector WorldExtent = Box->GetScaledBoxExtent();
	const float ColumnRadius = FMath::Min(WorldExtent.X, WorldExtent.Y);
	const FTransform VolumeTransform = Box->GetComponentTransform();
	for (int32 Index = 0; Index < UpdraftShapes.Num(); ++Index)
	{
		UStaticMeshComponent* Shape = UpdraftShapes[Index];
		Shape->SetVisibility(bActive);
		if (!bActive)
		{
			continue;
		}

		if (Index < UpdraftRibbonCount)
		{
			const float Rise = FMath::Frac(Time * (0.24f + (Index % 3) * 0.024f) + Index * 0.20f);
			const float Radius = ColumnRadius * FMath::Lerp(0.59f, 1.10f, Rise) / 100.f;
			const float Height = WorldExtent.Z * (0.40f + (Index % 3) * 0.08f) / 100.f;
			const float Yaw = FMath::Fmod(Time * 42.f + Index * 137.f, 360.f);
			const float Z = Extent.Z * FMath::Lerp(-0.82f, 0.91f, Rise);
			Shape->SetWorldTransform(FTransform(FRotator(0.f, Yaw, 0.f),
				VolumeTransform.TransformPosition(FVector(0.f, 0.f, Z)), FVector(Radius, Radius, Height)));
			if (UMaterialInstanceDynamic* RibbonMaterial = Cast<UMaterialInstanceDynamic>(Shape->GetMaterial(0)))
			{
				const float Fade = FMath::SmoothStep(0.f, 0.20f, Rise) * (1.f - FMath::SmoothStep(0.76f, 1.f, Rise));
				RibbonMaterial->SetScalarParameterValue(FlowOpacityParameter, Fade);
			}
			continue;
		}

		const float Rise = FMath::Frac(Time * (0.37f + (Index % 4) * 0.035f) + Index * 0.618f);
		const float Angle = Index * 2.40f + Rise * 4.1f;
		float Sine, Cosine;
		FMath::SinCos(&Sine, &Cosine, Angle);
		const float Radius = FMath::Lerp(0.36f, 0.66f, Rise);
		const FVector Local(Extent.X * Radius * Cosine, Extent.Y * Radius * Sine,
			Extent.Z * FMath::Lerp(-0.88f, 0.90f, Rise));
		const float Fade = FMath::SmoothStep(0.f, 0.14f, Rise) * (1.f - FMath::SmoothStep(0.78f, 1.f, Rise));
		const FRotator Rotation(Rise * 260.f, Index * 41.f + Rise * 170.f, 30.f + Index * 53.f);
		const float Size = (0.75f + (Index % 4) * 0.10f) * Fade;
		Shape->SetWorldTransform(FTransform(Rotation, VolumeTransform.TransformPosition(Local),
			FVector(0.34f * Size, 0.21f * Size, 1.f)));
	}
}
