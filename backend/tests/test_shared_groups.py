import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, VM, VMGroup
from app.schemas import VMGroupCreate, VMGroupUpdate, VMCreate, VMUpdate
from app.routers.vms import (
    list_groups,
    create_group,
    update_group,
    delete_group,
    create_vm,
    update_vm,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db_session):
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password="pw",
        is_admin=True,
        is_active=True,
        max_vms=10,
        max_storage_gb=100,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def normal_user(db_session):
    user = User(
        username="player1",
        email="player1@example.com",
        hashed_password="pw",
        is_admin=False,
        is_active=True,
        max_vms=10,
        max_storage_gb=100,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    user = User(
        username="player2",
        email="player2@example.com",
        hashed_password="pw",
        is_admin=False,
        is_active=True,
        max_vms=10,
        max_storage_gb=100,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.anyio
async def test_admin_can_create_shared_group(db_session, admin_user):
    body = VMGroupCreate(
        name="LAN Arena",
        description="Public Deathmatch LAN",
        color="#ef4444",
        network_enabled=True,
        is_shared=True,
    )
    res = await create_group(body=body, db=db_session, current_user=admin_user)
    assert res.name == "LAN Arena"
    assert res.is_shared is True
    assert res.network_enabled is True
    assert res.owner_username == "admin"


@pytest.mark.anyio
async def test_non_admin_cannot_create_shared_group(db_session, normal_user):
    body = VMGroupCreate(
        name="Hacked LAN",
        network_enabled=True,
        is_shared=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_group(body=body, db=db_session, current_user=normal_user)
    assert exc_info.value.status_code == 403
    assert "Only administrators" in exc_info.value.detail


@pytest.mark.anyio
async def test_non_admin_can_create_private_group(db_session, normal_user):
    body = VMGroupCreate(
        name="My Private Group",
        network_enabled=True,
        is_shared=False,
    )
    res = await create_group(body=body, db=db_session, current_user=normal_user)
    assert res.name == "My Private Group"
    assert res.is_shared is False
    assert res.user_id == normal_user.id


@pytest.mark.anyio
async def test_list_groups_visibility(db_session, admin_user, normal_user, other_user):
    shared_group = VMGroup(name="Public LAN", user_id=admin_user.id, is_shared=True, network_enabled=True)
    admin_private = VMGroup(name="Admin Private", user_id=admin_user.id, is_shared=False)
    p1_group = VMGroup(name="Player1 Private", user_id=normal_user.id, is_shared=False)
    p2_group = VMGroup(name="Player2 Private", user_id=other_user.id, is_shared=False)

    db_session.add_all([shared_group, admin_private, p1_group, p2_group])
    db_session.commit()

    # Player 1 sees own private + shared, but not others' private
    res_p1 = await list_groups(db=db_session, current_user=normal_user)
    names_p1 = [g.name for g in res_p1]
    assert "Player1 Private" in names_p1
    assert "Public LAN" in names_p1
    assert "Admin Private" not in names_p1
    assert "Player2 Private" not in names_p1

    # Player 2 sees own private + shared
    res_p2 = await list_groups(db=db_session, current_user=other_user)
    names_p2 = [g.name for g in res_p2]
    assert "Player2 Private" in names_p2
    assert "Public LAN" in names_p2
    assert "Player1 Private" not in names_p2
    assert "Admin Private" not in names_p2


@pytest.mark.anyio
async def test_update_group_permissions(db_session, admin_user, normal_user):
    shared = VMGroup(name="Shared", user_id=admin_user.id, is_shared=True, network_enabled=True)
    p1_group = VMGroup(name="P1 Group", user_id=normal_user.id, is_shared=False)
    db_session.add_all([shared, p1_group])
    db_session.commit()

    # Normal user cannot update admin's shared group
    with pytest.raises(HTTPException) as exc_info:
        await update_group(
            group_id=shared.id,
            body=VMGroupUpdate(name="Renamed by non-admin"),
            db=db_session,
            current_user=normal_user,
        )
    assert exc_info.value.status_code == 403

    # Normal user cannot promote their own group to is_shared
    with pytest.raises(HTTPException) as exc_info:
        await update_group(
            group_id=p1_group.id,
            body=VMGroupUpdate(is_shared=True),
            db=db_session,
            current_user=normal_user,
        )
    assert exc_info.value.status_code == 403

    # Admin can update shared group
    res = await update_group(
        group_id=shared.id,
        body=VMGroupUpdate(name="New Shared Name"),
        db=db_session,
        current_user=admin_user,
    )
    assert res.name == "New Shared Name"


@pytest.mark.anyio
async def test_delete_group_permissions_and_unlink(db_session, admin_user, normal_user):
    shared = VMGroup(name="Shared", user_id=admin_user.id, is_shared=True, network_enabled=True)
    db_session.add(shared)
    db_session.commit()

    vm = VM(name="P1 VM", user_id=normal_user.id, group_id=shared.id, status="stopped", config={})
    db_session.add(vm)
    db_session.commit()

    # Normal user cannot delete shared group
    with pytest.raises(HTTPException) as exc_info:
        await delete_group(group_id=shared.id, db=db_session, current_user=normal_user)
    assert exc_info.value.status_code == 403

    # Admin can delete shared group, which unlinks the VM
    await delete_group(group_id=shared.id, db=db_session, current_user=admin_user)
    db_session.refresh(vm)
    assert vm.group_id is None
    assert db_session.query(VMGroup).filter(VMGroup.id == shared.id).first() is None


@pytest.mark.anyio
async def test_vm_group_assignment(db_session, admin_user, normal_user):
    shared = VMGroup(name="Shared LAN", user_id=admin_user.id, is_shared=True, network_enabled=True)
    admin_private = VMGroup(name="Admin Private", user_id=admin_user.id, is_shared=False)
    db_session.add_all([shared, admin_private])
    db_session.commit()

    # Normal user can assign their VM to the admin's shared group
    vm = VM(name="Doom Client 1", user_id=normal_user.id, group_id=None, status="stopped", config={})
    db_session.add(vm)
    db_session.commit()

    res = await update_vm(
        vm_id=vm.id,
        body=VMUpdate(group_id=shared.id),
        db=db_session,
        current_user=normal_user,
    )
    assert res.group_id == shared.id
    assert res.group_name == "Shared LAN"
    assert res.group_is_shared is True

    # Normal user cannot assign their VM to admin's private group
    with pytest.raises(HTTPException) as exc_info:
        await update_vm(
            vm_id=vm.id,
            body=VMUpdate(group_id=admin_private.id),
            db=db_session,
            current_user=normal_user,
        )
    assert exc_info.value.status_code == 404
