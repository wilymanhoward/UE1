#include "TrailCrosswind.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "LSGameInstance.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SeedBall.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 CrosswindLeafCount = 12;
	constexpr int32 CrosswindStreakCount = 4;
	constexpr float CrosswindCalm = 3.1f;
	constexpr float CrosswindWarning = 0.9f;
	constexpr float CrosswindGust = 1.45f;
	constexpr float CrosswindTail = 0.4f;
}

ATrailCrosswind::ATrailCrosswind()
{
	PrimaryActorTick.bCanEverTick = true;
	Box->SetBoxExtent(FVector(500.0, 400.0, 210.0));
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
	const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>();
	const bool bStoneUnlocked = GameInstance && GameInstance->IsFormUnlocked(ESeedForm::Stone);
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
		const bool bVisible = !bStoneUnlocked && Travel > 0.f && Travel < 1.f;
		Shape->SetVisibility(bVisible);
		if (!bVisible)
		{
			continue;
		}

		// The early leaves lift first on the forest side, then accelerate across the same lane as the gust.
		const float Sweep = bWarningLeaf ? Travel * Travel : Travel;
		const float Size = FMath::SmoothStep(0.f, 0.14f, Travel) * (1.f - FMath::SmoothStep(0.78f, 1.f, Travel));
		const float Along = static_cast<float>((Index * 263) % 920) - 460.f;
		const float Height = -42.f + (Index % 6) * 25.f + (bLeaf ? 42.f * FMath::Sin(Travel * 6.f + Index) : 15.f);
		const float Across = FMath::Lerp(-560.f, 520.f, Sweep);
		Shape->SetRelativeLocationAndRotation(FVector(Along, Across, Height), bLeaf
			? FRotator(Travel * 235.f + Index * 28.f, 90.f + Travel * 210.f, 35.f + Index * 21.f)
			: FRotator(0.f, 90.f, 70.f));
		Shape->SetRelativeScale3D(bLeaf ? FVector(0.23f * Size, 0.14f * Size, 1.f)
			: FVector((2.4f + (Index % 3) * 0.45f) * Size, 0.22f * Size, 1.f));
	}

	if (bStoneUnlocked)
	{
		SetActorTickEnabled(false);
		return;
	}

	const float GustAge = Age - CrosswindWarning;
	if (GustAge > 0.f && GustAge < CrosswindGust)
	{
		if (ASeedBall* Ball = GetBallInside())
		{
			const float Push = FMath::SmoothStep(0.f, 0.23f, GustAge)
				* (1.f - FMath::SmoothStep(CrosswindGust - 0.28f, CrosswindGust, GustAge));
			Ball->AddExternalAcceleration(GetActorRightVector() * (390.f * Push * Ball->GetCurrentFormData().WindResponse));
		}
	}
}
