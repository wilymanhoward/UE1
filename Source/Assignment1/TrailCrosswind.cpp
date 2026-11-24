#include "TrailCrosswind.h"

#include "Components/ArrowComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SeedBall.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 CrosswindLeafCount = 18;
	constexpr int32 CrosswindStreakCount = 7;
	constexpr float CrosswindOff = 2.f;
	constexpr float CrosswindWarning = 0.35f;
	constexpr float CrosswindGust = 2.f;
}

ATrailCrosswind::ATrailCrosswind()
{
	PrimaryActorTick.bCanEverTick = true;
	Box->SetBoxExtent(FVector(420.0, 1500.0, 1150.0));
#if WITH_EDITORONLY_DATA
	if (UArrowComponent* Direction = CreateEditorOnlyDefaultSubobject<UArrowComponent>(TEXT("GustDirection")))
	{
		Direction->SetupAttachment(Box);
		Direction->SetRelativeRotation(FRotator(0.0, 90.0, 0.0));
		Direction->ArrowSize = 4.f;
		Direction->ArrowColor = FColor::Cyan;
	}
#endif
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> WindMaterial(
		TEXT("/Game/LastSeed/Materials/M_LS_TrailCrosswind.M_LS_TrailCrosswind"));
	static ConstructorHelpers::FObjectFinder<USoundBase> WindAudio(
		TEXT("/Game/LastSeed/Audio/SFX_LS_TrailCrosswind.SFX_LS_TrailCrosswind"));
	GustSound = WindAudio.Object;

	for (int32 Index = 0; Index < CrosswindLeafCount + CrosswindStreakCount; ++Index)
	{
		const FName Name(*FString::Printf(TEXT("WindShape%d"), Index));
		UStaticMeshComponent* Shape = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Shape->SetupAttachment(Box);
		Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Shape->SetGenerateOverlapEvents(false);
		Shape->SetCastShadow(false);
		Shape->SetReceivesDecals(false);
		Shape->SetStaticMesh(Plane.Object);
		Shape->SetMaterial(0, WindMaterial.Object);
		Shape->SetVisibility(false);
		WindShapes.Add(Shape);
	}
}

void ATrailCrosswind::BeginPlay()
{
	Super::BeginPlay();

	if (UMaterialInstanceDynamic* LeafMaterial = WindShapes[0]->CreateDynamicMaterialInstance(0))
	{
		LeafMaterial->SetScalarParameterValue(TEXT("Leaf"), 1.f);
		for (int32 Index = 1; Index < CrosswindLeafCount; ++Index)
		{
			WindShapes[Index]->SetMaterial(0, LeafMaterial);
		}
	}
}

void ATrailCrosswind::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Period = CrosswindOff + CrosswindGust;
	const float Age = FMath::Fmod(GetWorld()->GetTimeSeconds(), Period) - (CrosswindOff - CrosswindWarning);
	const bool bGustAudible = Age >= 0.f;
	if (bGustAudible && !bGustAudioStarted && GustSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, GustSound, GetActorLocation(), 0.72f);
	}
	bGustAudioStarted = bGustAudible;
	for (int32 Index = 0; Index < WindShapes.Num(); ++Index)
	{
		UStaticMeshComponent* Shape = WindShapes[Index];
		const bool bLeaf = Index < CrosswindLeafCount;
		const bool bWarningLeaf = Index < 5;
		const float Delay = bWarningLeaf ? Index * 0.065f : CrosswindWarning + (Index % 5) * 0.12f;
		const float Duration = bWarningLeaf ? 1.50f : 1.52f;
		const float Travel = (Age - Delay) / Duration;
		const bool bVisible = Travel > 0.f && Travel < 1.f;
		Shape->SetVisibility(bVisible);
		if (!bVisible)
		{
			continue;
		}

		// The early leaves lift first on the forest side, then accelerate across the same lane as the gust.
		const float Sweep = bWarningLeaf ? Travel * Travel : Travel;
		const float Size = FMath::SmoothStep(0.f, 0.14f, Travel) * (1.f - FMath::SmoothStep(0.78f, 1.f, Travel));
		const float Drift = FMath::Sin(Travel * 5.f + Index);
		const float Along = static_cast<float>((Index * 263) % 780) - 390.f + Drift * (bLeaf ? 65.f : 24.f);
		const float Height = -58.f + (Index % 6) * 29.f + (bLeaf ? 56.f * Drift : 24.f * Drift);
		const float Across = FMath::Lerp(-690.f, 1030.f, Sweep);
		Shape->SetRelativeLocationAndRotation(FVector(Along, Across, Height), bLeaf
			? FRotator(Travel * 235.f + Index * 28.f, 90.f + Travel * 210.f, 35.f + Index * 21.f)
			: FRotator(4.f * Drift, 90.f, 62.f + 12.f * Drift));
		const float LeafSize = (0.80f + (Index % 4) * 0.14f) * Size;
		Shape->SetRelativeScale3D(bLeaf ? FVector(0.39f * LeafSize, 0.25f * LeafSize, 1.f)
			: FVector((3.65f + (Index % 3) * 0.55f) * Size, (0.78f + (Index % 3) * 0.10f) * Size, 1.f));
	}

	const float GustAge = Age - CrosswindWarning;
	ASeedBall* Ball = GustAge > 0.f && GustAge < CrosswindGust ? GetBallInside() : nullptr;
	if (Ball && Ball->GetCurrentForm() == ESeedForm::Seed)
	{
		const float Push = FMath::SmoothStep(0.f, 0.18f, GustAge)
			* (1.f - FMath::SmoothStep(CrosswindGust - 0.28f, CrosswindGust, GustAge));
		Ball->AddExternalAcceleration(GetActorRightVector() * (1700.f * Push));
	}
}
