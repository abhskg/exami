from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicResponse

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("/", response_model=list[TopicResponse])
def list_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all topics created by the authenticated user.
    """
    return db.query(Topic).filter(Topic.user_id == current_user.id).order_by(Topic.created_at.desc()).all()

@router.post("/", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new topic for the authenticated user.
    """
    # Check if a topic with the same name already exists for this user
    existing = db.query(Topic).filter(
        Topic.user_id == current_user.id,
        Topic.name == topic_in.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic with name '{topic_in.name}' already exists."
        )
        
    topic = Topic(
        user_id=current_user.id,
        name=topic_in.name,
        description=topic_in.description
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic
