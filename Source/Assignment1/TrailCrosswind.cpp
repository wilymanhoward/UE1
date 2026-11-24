#include "TrailCrosswind.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SeedBall.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 CrosswindLeafCount = 18;
	constexpr int32 CrosswindStreakCount = 7;
	constexpr float CrosswindCalm = 3.3f;
	constexpr float CrosswindWarning = 0.9f;
	constexpr float CrosswindGust = 1.75f;
	constexpr float CrosswindTail = 0.4f;
	const FName CrosswindSoftTrailEdge(TEXT("LS_SoftTrailEdge"));
}

ATrailCrosswind::ATrailCrosswind()
{
	PrimaryActorTick.bCanEverTick = true;
	Box->SetBoxExtent(FVector(680.0, 1500.0, 1150.0));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> WindMaterial(
		TEXT("/Game/LastSeed/Materials/M_LS_TrailCrosswind.M_LS_TrailCrosswind"));

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

	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (!It->ActorHasTag(CrosswindSoftTrailEdge) || !It->GetActorEnableCollision())
		{
			continue;
		}
		const FVector Local = GetActorTransform().InverseTransformPositionNoScale(It->GetActorLocation());
		if (FMath::Abs(Local.X) < 960.f && Local.Y > 160.f && Local.Y < 1150.f)
		{
			RiverEdges.Add(*It);
		}
	}

	if (UMaterialInstanceDynamic* LeafMaterial = WindShapes[0]->CreateDynamicMaterialInstance(0))
	{
		LeafMaterial->SetScalarParameterValue(TEXT("Leaf"), 1.f);
		for (int32 Index = 1; Index < CrosswindLeafCount; ++Index)
		{
			WindShapes[Index]->SetMaterial(0, LeafMaterial);
		}
	}
}

void ATrailCrosswind::EndPlay(const EEndPlayReason::Type Reason)
{
	SetRiverEdgeOpen(false);
	Super::EndPlay(Reason);
}

void ATrailCrosswind::SetRiverEdgeOpen(bool bOpen)
{
	if (bRiverEdgeOpen == bOpen)
	{
		return;
	}
	bRiverEdgeOpen = bOpen;
	for (const TWeakObjectPtr<AActor>& Edge : RiverEdges)
	{
		if (Edge.IsValid())
		{
			Edge->SetActorEnableCollision(!bOpen);
		}
	}
}

void ATrailCrosswind::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Period = CrosswindCalm + CrosswindWarning + CrosswindGust + CrosswindTail;
	const float Age = FMath::Fmod(GetWorld()->GetTimeSeconds(), Period) - CrosswindCalm;
	for (int32 Index = 0; Index < WindShapes.Num(); ++Index)
	{
		UStaticMeshComponent* Shape = WindShapes[Index];
		const bool bLeaf = Index < CrosswindLeafCount;
		const bool bWarningLeaf = Index < 5;
		const float Delay = bWarningLeaf ? Index * 0.08f : CrosswindWarning - 0.23f + (Index % 5) * 0.10f;
		const float Duration = bWarningLeaf ? 1.85f : 1.24f;
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
		const float Along = static_cast<float>((Index * 263) % 1220) - 610.f;
		const float Height = -42.f + (Index % 6) * 25.f + (bLeaf ? 42.f * FMath::Sin(Travel * 6.f + Index) : 15.f);
		const float Across = FMath::Lerp(-690.f, 1030.f, Sweep);
		Shape->SetRelativeLocationAndRotation(FVector(Along, Across, Height), bLeaf
			? FRotator(Travel * 235.f + Index * 28.f, 90.f + Travel * 210.f, 35.f + Index * 21.f)
			: FRotator(0.f, 90.f, 70.f));
		Shape->SetRelativeScale3D(bLeaf ? FVector(0.28f * Size, 0.18f * Size, 1.f)
			: FVector((3.15f + (Index % 3) * 0.55f) * Size, 0.35f * Size, 1.f));
	}

	const float GustAge = Age - CrosswindWarning;
	ASeedBall* Ball = GustAge > 0.f && GustAge < CrosswindGust ? GetBallInside() : nullptr;
	const bool bCanBlowOffTrail = Ball && Ball->GetCurrentForm() == ESeedForm::Seed;
	// Open only the river side while a gust is carrying Seed, so the soft trail boundary can't catch it.
	SetRiverEdgeOpen(bCanBlowOffTrail);
	if (bCanBlowOffTrail)
	{
		const float Push = FMath::SmoothStep(0.f, 0.18f, GustAge)
			* (1.f - FMath::SmoothStep(CrosswindGust - 0.28f, CrosswindGust, GustAge));
		Ball->AddExternalAcceleration(GetActorRightVector() * (1700.f * Push));
	}
}
