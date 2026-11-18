#include "CollapsingStoneComponent.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "SeedBall.h"
#include "TimerManager.h"

UCollapsingStoneComponent::UCollapsingStoneComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UCollapsingStoneComponent::BeginPlay()
{
	Super::BeginPlay();
	TArray<AActor*> Actors;
	for (AActor* Support : SupportActors)
		if (IsValid(Support) && Support != GetOwner()) Actors.AddUnique(Support);
	Actors.Add(GetOwner());
	for (AActor* Actor : Actors)
	{
		Pieces.Add(Actor);
		OriginalPoses.Add(Actor->GetActorTransform());
		OriginalCollision.Add(Actor->GetActorEnableCollision());
		OriginalHidden.Add(Actor->IsHidden());
		TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
		for (UStaticMeshComponent* Mesh : Meshes) Mesh->SetMobility(EComponentMobility::Movable);
	}

	FVector Origin, Extent;
	GetOwner()->GetActorBounds(false, Origin, Extent);
	Sensor = NewObject<UBoxComponent>(GetOwner(), TEXT("CollapseDepartureSensor"));
	Sensor->SetupAttachment(GetOwner()->GetRootComponent());
	Sensor->SetAbsolute(false, true, true);
	Sensor->SetBoxExtent(FVector(FMath::Max(50.f, Extent.X - 20.f), FMath::Max(50.f, Extent.Y - 20.f), 85.f));
	Sensor->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Sensor->SetCollisionResponseToAllChannels(ECR_Ignore);
	Sensor->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Overlap);
	Sensor->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Sensor->SetGenerateOverlapEvents(true);
	Sensor->OnComponentBeginOverlap.AddDynamic(this, &UCollapsingStoneComponent::HandleArrival);
	Sensor->OnComponentEndOverlap.AddDynamic(this, &UCollapsingStoneComponent::HandleDeparture);
	Sensor->RegisterComponent();
	Sensor->SetWorldLocation(FVector(Origin.X, Origin.Y, Origin.Z + Extent.Z + 70.f));
}

void UCollapsingStoneComponent::HandleArrival(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (ASeedBall* Visitor = Cast<ASeedBall>(OtherActor))
	{
		Ball = Visitor;
		Ball->OnRespawned.AddUniqueDynamic(this, &UCollapsingStoneComponent::Rebuild);
	}
}

void UCollapsingStoneComponent::HandleDeparture(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	if (OtherActor == Ball && !bTriggered && !bCollapsing)
	{
		bTriggered = true;
		GetWorld()->GetTimerManager().SetTimer(CollapseTimer, this, &UCollapsingStoneComponent::BeginCollapse,
			FMath::Max(0.01f, CollapseDelay), false);
	}
}

void UCollapsingStoneComponent::BeginCollapse()
{
	bCollapsing = true;
	FallElapsed = 0.f;
	Sensor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	for (const TWeakObjectPtr<AActor>& Piece : Pieces)
		if (Piece.IsValid()) Piece->SetActorEnableCollision(false);
	SetComponentTickEnabled(true);
}

void UCollapsingStoneComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	FallElapsed += DeltaTime;
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		if (!Pieces[Index].IsValid()) continue;
		const float Alpha = FMath::Clamp((FallElapsed - Index * 0.025f) / FMath::Max(0.1f, FallDuration), 0.f, 1.f);
		FTransform Pose = OriginalPoses[Index];
		const float Side = Index % 2 ? -1.f : 1.f;
		Pose.AddToTranslation(FVector(Side * 35.f * Alpha, 15.f * Alpha, -FallDistance * Alpha * Alpha));
		Pose.ConcatenateRotation(FRotator(Side * 12.f * Alpha, 5.f * Alpha, -Side * 8.f * Alpha).Quaternion());
		Pieces[Index]->SetActorTransform(Pose, false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (FallElapsed >= FallDuration + Pieces.Num() * 0.025f)
	{
		for (const TWeakObjectPtr<AActor>& Piece : Pieces)
			if (Piece.IsValid()) Piece->SetActorHiddenInGame(true);
		SetComponentTickEnabled(false);
	}
}

void UCollapsingStoneComponent::Rebuild()
{
	GetWorld()->GetTimerManager().ClearTimer(CollapseTimer);
	SetComponentTickEnabled(false);
	bTriggered = false;
	bCollapsing = false;
	FallElapsed = 0.f;
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		if (!Pieces[Index].IsValid()) continue;
		Pieces[Index]->SetActorTransform(OriginalPoses[Index], false, nullptr, ETeleportType::TeleportPhysics);
		Pieces[Index]->SetActorHiddenInGame(OriginalHidden[Index]);
		Pieces[Index]->SetActorEnableCollision(OriginalCollision[Index]);
	}
	Sensor->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void UCollapsingStoneComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorld()->GetTimerManager().ClearTimer(CollapseTimer);
	if (IsValid(Ball)) Ball->OnRespawned.RemoveDynamic(this, &UCollapsingStoneComponent::Rebuild);
	Super::EndPlay(EndPlayReason);
}
